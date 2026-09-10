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
        "stalleddl": DownloadStatus.DOWNLOADING,
        "metadl": DownloadStatus.DOWNLOADING,
        "pauseddl": DownloadStatus.PENDING,
        "queueddl": DownloadStatus.PENDING,
        "checkingdl": DownloadStatus.PENDING,
        "forceddl": DownloadStatus.DOWNLOADING,
        "allocating": DownloadStatus.PENDING,
        "downloadingdl": DownloadStatus.DOWNLOADING,
        "uploading": DownloadStatus.COMPLETED,
        "stalledup": DownloadStatus.COMPLETED,
        "queuedup": DownloadStatus.COMPLETED,
        "checkingup": DownloadStatus.COMPLETED,
        "forcedup": DownloadStatus.COMPLETED,
        "pausedup": DownloadStatus.COMPLETED,
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
                        matched = self._find_torrent_by_path(download, torrents)
                        if matched:
                            download.torrent_hash = matched["hash"]
                            logger.info(
                                "Hash backfilled por source_folder",
                                download_id=download.id,
                                torrent_hash=matched["hash"],
                            )
                        else:
                            logger.warning(
                                "Download sem torrent_hash e sem match no qBittorrent",
                                download_id=download.id,
                                source_folder=download.source_folder,
                            )
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
                        download.transition_to(new_status)
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
                            "data": download.to_dict(),
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
                if download.season:
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
                        "Cannot organize series without season",
                        download_id=download.id
                    )
            elif download.type.value == "anime":
                if download.season:
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
                        "Cannot organize anime without season",
                        download_id=download.id
                    )

            if dest_path:
                download.transition_to(DownloadStatus.ORGANIZED)
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
    def _find_torrent_by_path(download: Download, torrents: list) -> Optional[dict]:
        """Match a hash-less download to a qBittorrent torrent via save_path.

        Returns the matched torrent dict, or None when ambiguous/missing.
        """
        target = (download.source_folder or "").rstrip("/")
        if not target:
            return None

        candidates = [
            torrent
            for torrent in torrents
            if (torrent.get("save_path") or "").rstrip("/") == target
        ]
        if len(candidates) == 1:
            return candidates[0]

        name_matches = [
            torrent
            for torrent in candidates
            if torrent.get("name") == download.torrent_name
        ]
        if len(name_matches) == 1:
            return name_matches[0]

        if candidates:
            logger.warning(
                "Múltiplos torrents no mesmo save_path; hash não backfilled",
                download_id=download.id,
                source_folder=target,
                candidates=len(candidates),
            )
        return None

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
