from flask import Blueprint, render_template, request, abort
from app.models.playlist import Playlist
from app.services.playlist_service import PlaylistService

playlists_bp = Blueprint("playlists", __name__, url_prefix="/playlists")


@playlists_bp.route("")
def list_view():
    search = request.args.get("search", "").strip() or None
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")
    playlists = PlaylistService.get_all_playlists(search=search, sort_by=sort_by, order=order)
    return render_template(
        "playlists.html",
        active_page="playlists",
        playlists=playlists,
        search=search or "",
        sort_by=sort_by,
        order=order,
    )


@playlists_bp.route("/<int:playlist_id>")
def explorer_view(playlist_id):
    playlist = PlaylistService.get_playlist_by_id(playlist_id)
    if not playlist:
        abort(404)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search = request.args.get("search", "").strip() or None
    sort_by = request.args.get("sort_by", "position")
    order = request.args.get("order", "asc")
    module_filter = request.args.get("module", "").strip() or None

    items, total_count, total_pages = PlaylistService.get_playlist_items(
        playlist_id=playlist_id,
        page=page,
        per_page=per_page,
        search=search,
        sort_by=sort_by,
        order=order,
        module_filter=module_filter,
    )

    return render_template(
        "playlist_explorer.html",
        active_page="playlists",
        playlist=playlist,
        items=items,
        page=page,
        per_page=per_page,
        total_count=total_count,
        total_pages=total_pages,
        search=search or "",
        sort_by=sort_by,
        order=order,
        module_filter=module_filter or "",
    )
