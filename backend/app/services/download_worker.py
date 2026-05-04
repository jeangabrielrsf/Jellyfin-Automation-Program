"""Background worker to monitor qBittorrent downloads and update database."""
import asyncio
from typing import Optional
from app.database import SessionLocal
from app.models.download import Download, DownloadStatus
from app.services.qbittorrent_service import QBittorrentService
from app.services.organizer_service import OrganizerService
from app.logging_config import get_logger

logger = get_logger(__name__)

class DownloadWorker:
    """Background worker that syncs qBittorrent download state with the database."""
    
    INTERVAL = 10  # seconds between syncs
    
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
        service = QBittorrentService()
        
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
                        await self._organize_completed_download(download)
                
                db.commit()
                
        finally:
            db.close()
            await service.close()
    
    async def _organize_completed_download(self, download: Download):
        """Organize files when a download completes."""
        try:
            organizer = OrganizerService()
            
            if download.type.value == "movie":
                logger.info(
                    "Movie download completed",
                    download_id=download.id,
                    title=download.title,
                    source_folder=download.source_folder
                )
            elif download.type.value in ("series", "anime"):
                if download.season and download.episode:
                    organizer.organize_series(
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
        except Exception as e:
            logger.error(
                "Failed to organize completed download",
                download_id=download.id,
                error=str(e)
            )
    
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
