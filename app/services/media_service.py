import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from extensions import db
from app.models.download_job import DownloadJob
from app.services.storage_service import StorageService

logger = logging.getLogger("playlistpilot.media")


class MediaService:
    SUPPORTED_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"}
    SUPPORTED_AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"}
    ALL_SUPPORTED = SUPPORTED_VIDEO_EXTS | SUPPORTED_AUDIO_EXTS

    @staticmethod
    def is_ffmpeg_available() -> bool:
        """Check if FFmpeg binary is installed and executable in PATH."""
        return shutil.which("ffmpeg") is not None

    @classmethod
    def inspect_local_file(cls, file_path: str) -> Dict[str, Any]:
        """Validate and inspect local media file path and metadata."""
        p = Path(file_path).resolve()
        if not p.exists():
            return {"valid": False, "error": f"File does not exist: {file_path}"}

        if not p.is_file():
            return {"valid": False, "error": f"Path is not a regular file: {file_path}"}

        ext = p.suffix.lower()
        if ext not in cls.ALL_SUPPORTED:
            return {
                "valid": False,
                "error": f"Unsupported media format '{ext}'. Supported: {', '.join(sorted(cls.ALL_SUPPORTED))}",
            }

        try:
            size_bytes = p.stat().st_size
            return {
                "valid": True,
                "path": str(p),
                "name": p.name,
                "extension": ext,
                "is_video": ext in cls.SUPPORTED_VIDEO_EXTS,
                "is_audio": ext in cls.SUPPORTED_AUDIO_EXTS,
                "size_bytes": size_bytes,
                "size_formatted": StorageService.format_bytes(size_bytes),
            }
        except Exception as e:
            return {"valid": False, "error": f"Error accessing file metadata: {str(e)}"}

    @classmethod
    def convert_or_extract_audio(
        cls,
        source_file: str,
        output_format: str = "mp3",
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract audio or convert format safely using FFmpeg argument arrays (NO shell strings).
        Preserves the source file by default.
        """
        if not cls.is_ffmpeg_available():
            return {
                "success": False,
                "error": "FFmpeg is not installed or not in PATH. Please install FFmpeg to enable media conversion.",
                "error_code": "FFMPEG_MISSING",
            }

        inspect = cls.inspect_local_file(source_file)
        if not inspect.get("valid"):
            return {"success": False, "error": inspect.get("error")}

        source_path = Path(source_file).resolve()
        dest_dir = Path(output_dir).resolve() if output_dir else source_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        target_ext = f".{output_format.lstrip('.').lower()}"
        output_file = dest_dir / f"{source_path.stem}_converted{target_ext}"

        # Prevent overwriting source file
        if output_file == source_path:
            output_file = dest_dir / f"{source_path.stem}_converted_out{target_ext}"

        # Safe argument array for subprocess
        cmd = ["ffmpeg", "-i", str(source_path), "-y"]

        if target_ext in cls.SUPPORTED_AUDIO_EXTS:
            # Audio extraction / conversion flags
            cmd.extend(["-vn", "-acodec", "libmp3lame" if target_ext == ".mp3" else "copy"])
        
        cmd.append(str(output_file))

        try:
            logger.info(f"Executing FFmpeg command: {' '.join(cmd)}")
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,  # 5 minutes safety limit
            )

            if res.returncode != 0:
                return {
                    "success": False,
                    "error": f"FFmpeg execution failed (code {res.returncode}): {res.stderr[-300:]}",
                }

            out_size = output_file.stat().st_size if output_file.exists() else 0
            return {
                "success": True,
                "output_path": str(output_file),
                "output_name": output_file.name,
                "size_bytes": out_size,
                "size_formatted": StorageService.format_bytes(out_size),
                "message": f"Media successfully converted to {target_ext}.",
            }

        except subprocess.TimeoutExpired:
            if output_file.exists():
                output_file.unlink()
            return {"success": False, "error": "Media processing timed out."}
        except Exception as e:
            return {"success": False, "error": f"Error running media processing: {str(e)}"}

    @classmethod
    def download_youtube_media(
        cls,
        video_id_or_url: str,
        output_dir: Union[str, Path],
        media_format: str = "video",
        quality: str = "best",
        progress_callback=None,
        cancel_check=None,
    ) -> Dict[str, Any]:
        """
        Download genuine YouTube video or audio directly into local system directory using yt-dlp.
        Supports resolution quality selection (1080p, 720p, 480p, 360p, MP3 Audio, or Best Available).
        Supports real-time byte & percentage progress reporting and user cancellation.
        """
        import yt_dlp

        dest_dir = Path(output_dir).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        url = video_id_or_url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://www.youtube.com/watch?v={url}"

        saved_file_path = [None]

        def progress_hook(d):
            if cancel_check and cancel_check():
                raise Exception("Download cancelled by user.")

            if d.get("status") == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                pct = 0.0
                if total > 0:
                    pct = round((downloaded / total) * 100, 1)
                elif "_percent_str" in d:
                    try:
                        clean_str = d["_percent_str"].replace("%", "").strip()
                        pct = float(clean_str)
                    except Exception:
                        pass
                if progress_callback:
                    try:
                        progress_callback({
                            "status": "downloading",
                            "percent": pct,
                            "downloaded_bytes": downloaded,
                            "total_bytes": total,
                        })
                    except TypeError:
                        progress_callback(pct, downloaded, total)

            elif d.get("status") == "finished":
                filename = d.get("filename")
                if filename:
                    saved_file_path[0] = str(Path(filename).resolve())
                if progress_callback:
                    try:
                        progress_callback({
                            "status": "finished",
                            "percent": 100.0,
                            "downloaded_bytes": d.get("total_bytes", 0),
                            "total_bytes": d.get("total_bytes", 0),
                        })
                    except TypeError:
                        progress_callback(100.0, d.get("total_bytes", 0), d.get("total_bytes", 0))

        # Output template in target local folder
        out_tmpl = str(dest_dir / "%(title).80s [%(id)s].%(ext)s")

        # Ensure Node.js in C:\Program Files is discoverable if present
        node_dir = Path("C:/Program Files")
        if (node_dir / "node.exe").exists() and str(node_dir) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{str(node_dir)};{os.environ.get('PATH', '')}"

        node_exe = Path(r"C:\Program Files\node.exe")
        node_cfg = {"path": str(node_exe)} if node_exe.exists() else {}

        ydl_opts = {
            "outtmpl": out_tmpl,
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "noplaylist": True,
            "windowsfilenames": True,
            "js_runtimes": {"node": node_cfg},
            "remote_components": ["ejs:github"],
        }

        has_ffmpeg = cls.is_ffmpeg_available()

        if media_format == "audio" or quality == "audio_mp3":
            if has_ffmpeg:
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                })
            else:
                ydl_opts.update({
                    "format": "bestaudio[ext=m4a]/bestaudio/best",
                })
        else:
            # Video: Strictly guarantee MP4 container
            if has_ffmpeg:
                height_limit = {
                    "1080p": 1080,
                    "720p": 720,
                    "480p": 480,
                    "360p": 360,
                }.get(quality)

                if height_limit:
                    fmt = (
                        f"bestvideo[height<={height_limit}][ext=mp4]+bestaudio[ext=m4a]/"
                        f"bestvideo[height<={height_limit}]+bestaudio/"
                        f"best[height<={height_limit}][ext=mp4]/"
                        f"best[height<={height_limit}]/best"
                    )
                else:
                    fmt = (
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                        "bestvideo+bestaudio/"
                        "best[ext=mp4]/best"
                    )

                ydl_opts.update({
                    "format": fmt,
                    "merge_output_format": "mp4",
                    "postprocessors": [{
                        "key": "FFmpegVideoRemuxer",
                        "preferedformat": "mp4",
                    }],
                })
            else:
                ydl_opts.update({
                    "format": "best[ext=mp4]/best",
                })

        try:
            logger.info(f"Starting yt-dlp download for URL: {url} -> {dest_dir}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                final_path = None
                if info:
                    pred = ydl.prepare_filename(info)
                    if media_format == "audio" or quality == "audio_mp3":
                        candidate = Path(pred).with_suffix(".mp3")
                    else:
                        candidate = Path(pred).with_suffix(".mp4")

                    if candidate.exists():
                        final_path = str(candidate.resolve())
                    elif Path(pred).exists():
                        final_path = str(Path(pred).resolve())

                if not final_path and saved_file_path[0] and Path(saved_file_path[0]).exists():
                    final_path = saved_file_path[0]

                # Ensure MP4 container for video if FFmpeg is available and file has different extension
                if final_path and Path(final_path).exists() and media_format != "audio" and quality != "audio_mp3":
                    p_final = Path(final_path)
                    if p_final.suffix.lower() != ".mp4" and has_ffmpeg:
                        mp4_candidate = p_final.with_suffix(".mp4")
                        try:
                            remux_cmd = ["ffmpeg", "-i", str(p_final), "-c", "copy", "-y", str(mp4_candidate)]
                            res_remux = subprocess.run(
                                remux_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                timeout=60,
                            )
                            if res_remux.returncode == 0 and mp4_candidate.exists():
                                p_final.unlink()
                                final_path = str(mp4_candidate.resolve())
                        except Exception as remux_err:
                            logger.warning(f"Could not remux {p_final.name} to mp4: {remux_err}")

                file_size = Path(final_path).stat().st_size if final_path and Path(final_path).exists() else 0
                return {
                    "success": True,
                    "output_path": final_path or str(dest_dir),
                    "title": info.get("title", "Video") if info else "Video",
                    "file_size": file_size,
                    "size_formatted": StorageService.format_bytes(file_size),
                }

        except Exception as e:
            err_msg = str(e)
            logger.error(f"yt-dlp download failed: {err_msg}", exc_info=True)
            return {"success": False, "error": err_msg}

    @classmethod
    def process_media_job(cls, job: DownloadJob):
        """Process a media conversion DownloadJob from background worker."""
        if not cls.is_ffmpeg_available():
            job.error_message = "FFmpeg is not installed on this system."
            job.transition_to(DownloadJob.STATUS_FAILED)
            db.session.commit()
            return

        source = job.media_item.source_id if job.media_item else ""
        res = cls.convert_or_extract_audio(source, output_format="mp3")
        
        if res.get("success"):
            job.output_path = res.get("output_path")
            job.progress_percent = 100.0
            job.transition_to(DownloadJob.STATUS_COMPLETED)
        else:
            job.error_message = res.get("error", "Media processing failed.")
            job.transition_to(DownloadJob.STATUS_FAILED)

        db.session.commit()
