import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
import requests
from flask import current_app


class YouTubeMetadataService:
    API_BASE = "https://www.googleapis.com/youtube/v3"

    @classmethod
    def extract_playlist_id(cls, url_or_id: str) -> Optional[str]:
        """
        Extract YouTube playlist ID from various URL formats or raw ID.
        Examples:
          - PL... (raw ID)
          - https://www.youtube.com/playlist?list=PL...
          - https://www.youtube.com/watch?v=xxx&list=PL...
        """
        if not url_or_id:
            return None
        text = url_or_id.strip()

        # If it looks like a clean playlist ID directly
        if re.match(r"^[A-Za-z0-9_-]{12,64}$", text) and (text.startswith("PL") or text.startswith("UU") or text.startswith("FL") or text.startswith("RD")):
            return text

        # Parse URL
        try:
            parsed = urlparse(text)
            query_params = parse_qs(parsed.query)
            if "list" in query_params:
                return query_params["list"][0]
        except Exception:
            pass

        return None

    @classmethod
    def extract_video_id(cls, url_or_id: str) -> Optional[str]:
        """
        Extract 11-character YouTube video ID from various URL formats or raw ID.
        Examples:
          - dQw4w9WgXcQ
          - https://www.youtube.com/watch?v=dQw4w9WgXcQ
          - https://youtu.be/dQw4w9WgXcQ
          - https://m.youtube.com/watch?v=dQw4w9WgXcQ
          - https://www.youtube.com/shorts/dQw4w9WgXcQ
          - https://www.youtube.com/embed/dQw4w9WgXcQ
        """
        if not url_or_id:
            return None
        text = url_or_id.strip()

        # Clean 11-char video ID directly
        if re.match(r"^[A-Za-z0-9_-]{11}$", text):
            return text

        # Regex extraction
        patterns = [
            r"(?:v=|\/shorts\/|\/embed\/|\/v\/|youtu\.be\/|\/watch\?.*v=)([A-Za-z0-9_-]{11})",
            r"^([A-Za-z0-9_-]{11})$",
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                return match.group(1)

        try:
            parsed = urlparse(text)
            if "youtube.com" in (parsed.netloc or ""):
                qs = parse_qs(parsed.query)
                if "v" in qs and qs["v"]:
                    return qs["v"][0]
            elif "youtu.be" in (parsed.netloc or ""):
                path = parsed.path.strip("/")
                if len(path) == 11:
                    return path
        except Exception:
            pass

        return None

    @classmethod
    def fetch_single_video_metadata(cls, url_or_id: str) -> Dict[str, Any]:
        """
        Extract metadata for a single YouTube video or Short without downloading.
        Returns title, duration, thumbnail, author, and clean URL.
        """
        import yt_dlp
        v_id = cls.extract_video_id(url_or_id)
        url = url_or_id.strip()
        if v_id and not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={v_id}"

        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {"success": False, "error": "Could not retrieve video details."}

                vid_id = info.get("id") or v_id or "unknown"
                title = info.get("title") or "YouTube Video"
                duration = int(info.get("duration") or 0)
                thumbs = info.get("thumbnails", [])
                thumb_url = (
                    thumbs[-1].get("url")
                    if thumbs
                    else (f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg" if vid_id else "/static/images/placeholder-thumbnail.svg")
                )
                uploader = info.get("uploader") or info.get("channel") or ""

                return {
                    "success": True,
                    "video": {
                        "id": vid_id,
                        "title": title,
                        "duration_seconds": duration,
                        "thumbnail_url": thumb_url,
                        "uploader": uploader,
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                    }
                }
        except Exception as e:
            # Fallback if network/API limits metadata extraction: return minimal info if we have video ID
            if v_id:
                return {
                    "success": True,
                    "video": {
                        "id": v_id,
                        "title": f"YouTube Video ({v_id})",
                        "duration_seconds": 0,
                        "thumbnail_url": f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
                        "uploader": "YouTube",
                        "url": f"https://www.youtube.com/watch?v={v_id}",
                    }
                }
            return {"success": False, "error": f"Failed to retrieve video info: {str(e)}"}

    @classmethod
    def extract_channel_id_or_handle(cls, url_or_id: str) -> Optional[str]:
        """Extract channel ID or handle from URL or raw string."""
        if not url_or_id:
            return None
        text = url_or_id.strip()

        if text.startswith("UC") and len(text) == 24:
            return text

        if text.startswith("@"):
            return text

        try:
            parsed = urlparse(text)
            path_parts = [p for p in parsed.path.split("/") if p]
            if "channel" in path_parts:
                idx = path_parts.index("channel")
                if idx + 1 < len(path_parts):
                    return path_parts[idx + 1]
            if path_parts and path_parts[0].startswith("@"):
                return path_parts[0]
        except Exception:
            pass

        return None

    @classmethod
    def fetch_playlist_metadata(cls, url_or_id: str, max_items: int = 200) -> Dict[str, Any]:
        """
        Fetch playlist details and items from YouTube Data API v3.
        Gracefully handles missing API key, network errors, invalid IDs, and quota exhaustion.
        """
        api_key = current_app.config.get("YOUTUBE_API_KEY", "").strip() if current_app else ""
        if not api_key:
            logger_res = cls.fetch_playlist_with_ytdlp(url_or_id, max_items)
            if logger_res.get("success"):
                return logger_res
            return {
                "success": False,
                "error": "YouTube Data API key is not configured and direct extraction failed. Please check the playlist URL or enter an API key in Settings.",
                "error_code": "MISSING_API_KEY",
            }

        playlist_id = cls.extract_playlist_id(url_or_id)
        if not playlist_id:
            # Try direct yt-dlp extraction before giving up
            ytdlp_res = cls.fetch_playlist_with_ytdlp(url_or_id, max_items)
            if ytdlp_res.get("success"):
                return ytdlp_res
            return {
                "success": False,
                "error": "Invalid YouTube playlist URL or ID format. Expected a valid playlist link (e.g. 'https://www.youtube.com/playlist?list=PL...').",
                "error_code": "INVALID_URL",
            }

        try:
            # 1. Fetch Playlist details
            info_url = f"{cls.API_BASE}/playlists"
            info_params = {
                "part": "snippet,contentDetails",
                "id": playlist_id,
                "key": api_key,
            }
            resp = requests.get(info_url, params=info_params, timeout=10)
            if resp.status_code == 403:
                # Quota exceeded or key error - seamless fallback to yt-dlp!
                ytdlp_res = cls.fetch_playlist_with_ytdlp(url_or_id, max_items)
                if ytdlp_res.get("success"):
                    return ytdlp_res
                err_data = resp.json().get("error", {})
                return {
                    "success": False,
                    "error": f"YouTube API quota exceeded or key unauthorized: {err_data.get('message', 'Access denied')}",
                    "error_code": "QUOTA_EXCEEDED",
                }
            elif resp.status_code == 404:
                return {
                    "success": False,
                    "error": f"Playlist '{playlist_id}' was not found. Please verify the URL.",
                    "error_code": "NOT_FOUND",
                }
            elif resp.status_code != 200:
                return {
                    "success": False,
                    "error": f"YouTube API responded with error HTTP {resp.status_code}: {resp.text[:150]}",
                    "error_code": "API_ERROR",
                }

            data = resp.json()
            items_list = data.get("items", [])
            if not items_list:
                return {
                    "success": False,
                    "error": f"No playlist found matching ID: {playlist_id}",
                    "error_code": "EMPTY_PLAYLIST",
                }

            snippet = items_list[0].get("snippet", {})
            title = snippet.get("title", "Untitled YouTube Playlist")
            description = snippet.get("description", "")
            thumbnails = snippet.get("thumbnails", {})
            thumb_url = thumbnails.get("medium", {}).get("url") or thumbnails.get("default", {}).get("url") or "/static/images/placeholder-thumbnail.svg"

            # 2. Fetch Playlist Items (paginated)
            items_url = f"{cls.API_BASE}/playlistItems"
            page_token = None
            collected_items = []
            position = 1

            while len(collected_items) < max_items:
                items_params = {
                    "part": "snippet,contentDetails",
                    "playlistId": playlist_id,
                    "maxResults": min(50, max_items - len(collected_items)),
                    "key": api_key,
                }
                if page_token:
                    items_params["pageToken"] = page_token

                item_resp = requests.get(items_url, params=items_params, timeout=10)
                if item_resp.status_code != 200:
                    break

                item_data = item_resp.json()
                raw_items = item_data.get("items", [])
                if not raw_items:
                    break

                for r in raw_items:
                    snip = r.get("snippet", {})
                    v_id = snip.get("resourceId", {}).get("videoId")
                    if not v_id:
                        continue
                    v_title = snip.get("title", "Untitled Video")
                    v_thumbs = snip.get("thumbnails", {})
                    v_thumb = v_thumbs.get("medium", {}).get("url") or v_thumbs.get("default", {}).get("url") or "/static/images/placeholder-thumbnail.svg"
                    
                    collected_items.append({
                        "position": position,
                        "source_id": v_id,
                        "title": v_title,
                        "duration_seconds": 0,
                        "media_type": "video",
                        "thumbnail_url": v_thumb,
                        "availability_status": "available" if v_title != "Private video" and v_title != "Deleted video" else "unavailable",
                        "metadata": {
                            "channelTitle": snip.get("channelTitle", ""),
                            "publishedAt": snip.get("publishedAt", ""),
                            "is_youtube": True,
                        }
                    })
                    position += 1

                page_token = item_data.get("nextPageToken")
                if not page_token:
                    break

            return {
                "success": True,
                "playlist": {
                    "title": title,
                    "source_id": playlist_id,
                    "source_url": f"https://www.youtube.com/playlist?list={playlist_id}",
                    "source_type": "youtube",
                    "description": description,
                    "thumbnail_url": thumb_url,
                    "item_count": len(collected_items),
                },
                "items": collected_items,
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Connection to YouTube API timed out. Please check your network connection.",
                "error_code": "TIMEOUT",
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Network error communicating with YouTube: {str(e)}",
                "error_code": "NETWORK_ERROR",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error processing YouTube playlist: {str(e)}",
                "error_code": "INTERNAL_ERROR",
            }

    @classmethod
    def fetch_playlist_with_ytdlp(cls, url_or_id: str, max_items: int = 200) -> Dict[str, Any]:
        """
        Extract playlist metadata directly using yt-dlp without consuming Google API quota.
        Works seamlessly with any public playlist link or video URL.
        """
        import yt_dlp

        url = url_or_id.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            if len(url) == 11:
                url = f"https://www.youtube.com/watch?v={url}"
            else:
                url = f"https://www.youtube.com/playlist?list={url}"

        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {"success": False, "error": "No playlist information found."}

                # Single video fallback if a video URL was supplied
                entries = info.get("entries")
                if entries is None:
                    entries = [info]

                collected_items = []
                for idx, entry in enumerate(entries, 1):
                    if not entry or len(collected_items) >= max_items:
                        break

                    v_id = entry.get("id") or entry.get("url")
                    v_title = entry.get("title") or f"Video #{idx}"
                    v_duration = int(entry.get("duration") or 0)
                    v_thumbs = entry.get("thumbnails", [])
                    thumb_url = v_thumbs[0].get("url") if v_thumbs else "/static/images/placeholder-thumbnail.svg"

                    collected_items.append({
                        "position": idx,
                        "source_id": v_id,
                        "title": v_title,
                        "duration_seconds": v_duration,
                        "media_type": "video",
                        "thumbnail_url": thumb_url,
                        "availability_status": "available",
                        "metadata": {
                            "uploader": entry.get("uploader", ""),
                            "is_youtube": True,
                        }
                    })

                playlist_title = info.get("title") or "Imported YouTube Playlist"
                return {
                    "success": True,
                    "playlist": {
                        "title": playlist_title,
                        "source_id": info.get("id") or cls.extract_playlist_id(url) or "PL_IMPORTED",
                        "source_url": url,
                        "source_type": "youtube",
                        "description": info.get("description") or f"Imported with {len(collected_items)} items.",
                        "thumbnail_url": collected_items[0]["thumbnail_url"] if collected_items else "/static/images/placeholder-thumbnail.svg",
                        "item_count": len(collected_items),
                    },
                    "items": collected_items,
                }

        except Exception as e:
            return {"success": False, "error": f"Failed to extract playlist: {str(e)}"}
