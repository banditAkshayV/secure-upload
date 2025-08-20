import os, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
from .models import db, Comment, Entry
from .limits import limiter
import re

main_bp = Blueprint("main", __name__)

ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg"}

def verify_image(fp_path):
    """Check if uploaded file is a valid image, return (ok, format, (w,h))."""
    try:
        with Image.open(fp_path) as im:
            im.verify()
        with Image.open(fp_path) as im:
            image_format = (im.format or "").upper()
            width, height = im.size
            # Re-save to normalize and strip metadata
            im.convert("RGB").save(fp_path)
        return True, image_format, (width, height)
    except (UnidentifiedImageError, OSError):
        return False, None, None

def validate_comment_input(text):
    """Minimal validation: allow raw text, only limit excessive size."""
    if not isinstance(text, str):
        return False, "Invalid comment input"
    if len(text) > 10000:
        return False, "Comment too long"
    return True, "Valid input"

@main_bp.route("/", methods=["GET", "POST"])
@limiter.limit("100/minute; 1000/hour")
def home():
    if request.method == "POST":
        # Handle comment; store raw text exactly as entered
        text = request.form.get("comment", "")
        
        # Validate comment input
        is_valid, validation_msg = validate_comment_input(text)
        if not is_valid:
            flash(f"Input validation failed: {validation_msg}")
            return redirect(url_for("main.home"))

        # Handle image upload (optional)
        image_filename = None
        f = request.files.get("file")
        if f and f.filename:
            ext = os.path.splitext(f.filename)[1].lower()
            mimetype = (f.mimetype or "").lower()
            if ext not in ALLOWED_EXTS:
                flash("That extension isn't on the guest list. .png, .jpg, .jpeg only XD. nice try though.")
            elif mimetype not in ALLOWED_MIME_TYPES:
                flash(f"We asked for an image, not '{mimetype}'. Foiled again, hacker friend.")
            else:
                # Optional: light check for ext vs mime mismatch
                if (ext == ".png" and mimetype != "image/png") or (ext in {".jpg", ".jpeg"} and mimetype != "image/jpeg"):
                    flash("Disguising a file type? Bold. Unfortunately, we can see the mustache.")
                else:
                    unique_name = f"{uuid.uuid4().hex}{ext}"
                    dest = os.path.join(current_app.config["UPLOAD_DIR"], unique_name)
                    f.save(dest)

                    ok, fmt, dims = verify_image(dest)
                    if not ok:
                        os.remove(dest)
                        flash("Your 'image' failed a basic sniff test. Better luck on your next exploit attempt.")
                    else:
                        # Enforce real format vs extension to defeat cosplay
                        if fmt == "PNG" and ext != ".png":
                            os.remove(dest)
                            flash("Says PNG, dresses as JPEG. Identity crisis detected.")
                        elif fmt == "JPEG" and ext not in {".jpg", ".jpeg"}:
                            os.remove(dest)
                            flash("That JPEG tried to sneak in with the wrong badge. Denied.")
                        elif fmt not in {"PNG", "JPEG"}:
                            os.remove(dest)
                            flash("Exotic format. Cool. Unsupported. Bye.")
                        else:
                            image_filename = unique_name
                            flash("Fine. Your image checks out.")

        # Create a unified entry only if there is something to save
        if text or image_filename:
            try:
                # Store raw text; keep filenames validated by image pipeline
                entry = Entry(text=text or None, image_filename=image_filename)
                db.session.add(entry)
                db.session.commit()
                if text and not image_filename:
                    flash("Comment saved.")
            except Exception as e:
                flash("An error occurred while saving. Please try again.")
                db.session.rollback()
                current_app.logger.error(f"Database error: {str(e)}")
        else:
            flash("Submitted nothing? That's one way to avoid getting caught. Still a no.")

        return redirect(url_for("main.home"))

    try:
        # Fetch recent entries
        entries = Entry.query.order_by(Entry.id.desc()).limit(100).all()
                
    except Exception as e:
        current_app.logger.error(f"Error fetching entries: {str(e)}")
        entries = []
        flash("Error loading entries. Please try again later.")

    return render_template(
        "home.html",
        entries=entries,
        max_size_bytes=current_app.config.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024),
        allowed_exts=sorted(ALLOWED_EXTS),
        allowed_mimes=sorted(ALLOWED_MIME_TYPES),
    )

@main_bp.route("/uploads/<filename>")
@limiter.limit("100/minute; 1000/hour")
def uploaded_file(filename):
    """Serve uploaded images safely."""
    # Additional filename validation
    if not filename or not re.match(r'^[a-f0-9]{32}\.(png|jpg|jpeg)$', filename):
        abort(404)
    
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename)


@main_bp.app_errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(e):
    """Handle payloads over MAX_CONTENT_LENGTH with a redirect and a snarky note."""
    max_bytes = current_app.config.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)
    max_mb = round(max_bytes / 1024 / 1024)
    flash(f"The data value transmitted exceeds the capacity limit. That file is thicc. Our {max_mb}MB door says no. Shrink it and try again, mastermind.")
    return redirect(url_for("main.home"))


@main_bp.app_errorhandler(429)
def ratelimit_handler(e):
    flash("Slow down, speedrunner. Requests per minute are capped. Take a sip of water and try again.")
    return redirect(url_for("main.home"))
