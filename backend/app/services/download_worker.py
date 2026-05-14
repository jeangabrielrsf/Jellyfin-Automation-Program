"""Background worker to monitor qBittorrent downloads and update database."""
import asyncio
from typing import Optional, Callable, Awaitable
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.download import Download, DownloadStatus
from app.services.qbittorrent_service import QBittorrentService
from app.services.organizer_service import OrganizerService
from app.logging_config import get_logger

logger = get_logger(__name__)

class DownloadWorker:
    """Background worker that syncs qBittorrent download state with the database."""
    
    INTERVAL = 10  # seconds between syncs
    
    def __init__(self, broadcast_callback: Optional[Callable[[dict], Awaitable[None]]] = None):
        self.broadcast_callback = broadcast_callback
    
    # qBittorrent state → app status mapping
    STATE_MAPPING = {
        "downloading": DownloadStatus.DOWNLOADING,
        "stalledDL": DownloadStatus.DOWNLOADING,
        "metaDL": DownloadStatus.DOWNLOADING,
        "pausedDL": DownloadStatus.PENDING,
        "queuedDL": DownloadStatus.PENDING,
        "checkingDL": DownloadStatus.PENDING,
        "forcedDL": DownloadStatus.DOWNLOADING,
        "allocating": DownloadStatus.PENDING,
        "downloadingDL": DownloadStatus.DOWNLOADING,
        "uploading": DownloadStatus.COMPLETED,
        "stalledUP": DownloadStatus.COMPLETED,
        "queuedUP": DownloadStatus.COMPLETED,
        "checkingUP": DownloadStatus.COMPLETED,
        "forcedUP": DownloadStatus.COMPLETED,
        "pausedUP": DownloadStatus.COMPLETED,
    }
    
    async def start(self):
        """Start the worker loop."""
        logger.info("DownloadWorker started")
        while True:
            try:
                await self._sync_progress()
            except Exception as e:
                logger.error("Error in DownloadWorker sync", error=str(e))
            await asyncio.sleep(self.INTERVAL)
    
    async def _sync_progress(self):
        """Sync download progress from qBittorrent to database."""
        db = SessionLocal()

        try:
            # Get all downloading downloads from DB
            downloading_statuses = [
                DownloadStatus.DOWNLOADING,
                DownloadStatus.PENDING
            ]
            downloads = db.query(Download).filter(
                Download.status.in_(downloading_statuses)
            ).all()

            if not downloads:
                return

            service = QBittorrentService(db=db)
            try:
                # Get all torrents from qBittorrent
                torrents = await service.get_torrents()

                # Build hash → torrent lookup
                torrent_map = {t["hash"].lower(): t for t in torrents if t.get("hash")}

                for download in downloads:
                    if not download.torrent_hash:
                        continue

                    torrent = torrent_map.get(download.torrent_hash.lower())
                    if not torrent:
                        logger.warning(
                            "Torrent not found in qBittorrent",
                            download_id=download.id,
                            torrent_hash=download.torrent_hash
                        )
                        continue

                    # Update progress
                    download.progress = torrent.get("progress", 0.0)
                    download.speed = self._format_speed(torrent.get("dlspeed", 0))
                    download.eta = self._format_eta(torrent.get("eta", 0))
                    download.seeds = torrent.get("num_seeds") or torrent.get("seeds")
                    download.peers = torrent.get("num_leechs") or torrent.get("peers")

                    # Map qBittorrent state to app status
                    qb_state = torrent.get("state", "").lower()
                    new_status = self.STATE_MAPPING.get(qb_state)

                    if new_status and new_status != download.status:
                        old_status = download.status
                        download.status = new_status
                        logger.info(
                            "Download status changed",
                            download_id=download.id,
                            old_status=old_status.value if old_status else None,
                            new_status=new_status.value,
                            progress=download.progress
                        )

                        # Trigger organization when completed
                        if new_status == DownloadStatus.COMPLETED:
                            await self._organize_completed_download(download, db)

                    db.commit()

                    # Broadcast update via WebSocket if callback is set
                    if self.broadcast_callback:
                        await self.broadcast_callback({
                            "type": "download_update",
                            "data": self._download_to_dict(download),
                        })
            finally:
                await service.close()

        finally:
            db.close()
    
    async def _organize_completed_download(self, download: Download, db: Session):
        """Organize files when a download completes."""
        service = QBittorrentService(db=db)
        torrent_hash = download.torrent_hash
        was_paused = False

        try:
            if torrent_hash:
                was_paused = await service.pause_torrent(torrent_hash)
                if was_paused:
                    await asyncio.sleep(1)

            organizer = OrganizerService(db=db)
            dest_path = None

            if download.type.value == "movie":
                dest_path = await organizer.organize_movie(
                    source_path=download.source_folder,
                    title=download.title,
                    year=None,
                    quality=download.quality or "1080p"
                )
                logger.info(
                    "Movie organized",
                    download_id=download.id,
                    title=download.title,
                    destination=dest_path
                )
            elif download.type.value == "series":
                if download.season and download.episode:
                    dest_path = await organizer.organize_series(
                        source_path=download.source_folder,
                        title=download.title,
                        season=download.season,
                        episode=download.episode,
                        quality=download.quality or "1080p"
                    )
                    logger.info(
                        "Organized series download",
                        download_id=download.id,
                        title=download.title,
                        season=download.season,
                        episode=download.episode
                    )
                else:
                    logger.warning(
                        "Cannot organize series without season/episode",
                        download_id=download.id
                    )
            elif download.type.value == "anime":
                if download.season and download.episode:
                    dest_path = await organizer.organize_anime(
                        source_path=download.source_folder,
                        title=download.title,
                        season=download.season,
                        episode=download.episode,
                        quality=download.quality or "1080p"
                    )
                    logger.info(
                        "Organized anime download",
                        download_id=download.id,
                        title=download.title,
                        season=download.season,
                        episode=download.episode
                    )
                else:
                    logger.warning(
                        "Cannot organize anime without season/episode",
                        download_id=download.id
                    )

            if dest_path:
                download.status = DownloadStatus.ORGANIZED
                download.destination_folder = dest_path
                db.commit()

            if torrent_hash:
                await service.delete_torrent(torrent_hash, delete_files=False)

        except Exception as e:
            logger.error(
                "Failed to organize completed download",
                download_id=download.id,
                error=str(e)
            )
            if was_paused and torrent_hash:
                try:
                    await service.resume_torrent(torrent_hash)
                except Exception as resume_error:
                    logger.error(
                        "Failed to resume torrent after organize failure",
                        download_id=download.id,
                        error=str(resume_error)
                    )
        finally:
            await service.close()
    
    @staticmethod
    def _format_speed(speed_bytes: int) -> str:
        """Format download speed in human readable format."""
        if speed_bytes == 0:
            return "0 B/s"
        
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        unit_index = 0
        speed = float(speed_bytes)
        
        while speed >= 1024 and unit_index < len(units) - 1:
            speed /= 1024
            unit_index += 1
        
        return f"{speed:.1f} {units[unit_index]}"
    
    @staticmethod
    def _format_eta(eta_seconds: int) -> str:
        """Format ETA in human readable format."""
        if eta_seconds == 0 or eta_seconds >= 8640000:
            return "Unknown"
        
        hours = eta_seconds // 3600
        minutes = (eta_seconds % 3600) // 60
        seconds = eta_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def _download_to_dict(download: Download) -> dict:
        """Serialize a Download model to a JSON-safe dict."""
        return {
            "id": download.id,
            "tmdb_id": download.tmdb_id,
            "title": download.title,
            "type": download.type.value if download.type else None,
            "season": download.season,
            "episode": download.episode,
            "torrent_name": download.torrent_name,
            "torrent_hash": download.torrent_hash,
            "magnet_link": download.magnet_link,
            "quality": download.quality,
            "language_preference": download.language_preference,
            "status": download.status.value if download.status else None,
            "progress": download.progress,
            "speed": download.speed,
            "eta": download.eta,
            "source_folder": download.source_folder,
            "destination_folder": download.destination_folder,
            "indexer_used": download.indexer_used,
            "seeds": download.seeds,
            "peers": download.peers,
            "error_message": download.error_message,
            "created_at": download.created_at.isoformat() if download.created_at else None,
            "updated_at": download.updated_at.isoformat() if download.updated_at else None,
            "completed_at": download.completed_at.isoformat() if download.completed_at else None,
        }
