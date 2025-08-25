import os, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, session, abort
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
from .database import insert_entry, get_recent_entries, get_total_entries_count
from .limits import limiter
import secrets
import re
import threading
import time


main_bp = Blueprint("main", __name__)

ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg"}


def verify_image_with_timeout(fp_path, timeout=5):
    """Verify image in a separate thread with timeout"""
    result = [None, None, None]  # [success, format, dimensions]
    exception = [None]
    
    def _verify():
        try:
            # Use PIL's built-in size checking before processing
            with Image.open(fp_path) as im:
                # Check dimensions BEFORE any processing
                width, height = im.size
                total_pixels = width * height
                
                # Hard pixel limit check
                if total_pixels > 25000000:  # 25M pixels (reduced from 50M)
                    result[0] = False
                    return
                    
                # Check aspect ratio for suspicious images
                if width > 0 and height > 0:
                    aspect_ratio = max(width, height) / min(width, height)
                    if aspect_ratio > 100:  # Suspicious aspect ratio
                        result[0] = False
                        return
                
                # Now verify the image is actually valid
                im.verify()
                
            # If we get here, image passed all checks - now process it
            with Image.open(fp_path) as im:
                image_format = (im.format or "").upper()
                # Re-save to normalize and strip metadata
                im.convert("RGB").save(fp_path)
                
            result[0] = True
            result[1] = image_format
            result[2] = (width, height)
            
        except Exception as e:
            exception[0] = e
            result[0] = False
    
    # Run verification in separate thread
    thread = threading.Thread(target=_verify)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        # Thread is still running - timeout occurred
        return False, None, None
    
    if exception[0]:
        # Exception occurred during processing
        return False, None, None
        
    return result[0], result[1], result[2]

def verify_image(fp_path):
    """Check if uploaded file is a valid image, return (ok, format, (w,h))."""
    try:
        # First, check file size to prevent obvious bombs
        file_size = os.path.getsize(fp_path)
        if file_size > 10 * 1024 * 1024:  # 10MB hard limit
            return False, None, None
            
        # Use timeout-protected verification
        return verify_image_with_timeout(fp_path, timeout=5)
        
    except (UnidentifiedImageError, OSError, MemoryError):
        return False, None, None

def detect_injection_attempts(text):
    """Detect common injection attempts and return sarcastic messages."""
    if not text or not isinstance(text, str):
        return None
    
    text_lower = text.lower()
    
    # SQL Injection patterns
    sql_patterns = [
        (r'\b(union|select|insert|update|delete|drop|create|alter)\b', 
         "🤖 SQL Injection detected! Nice try, script kiddie. Your 'hack' is now preserved as plain text for eternity."),
        (r'(\'|\").*(\bor\b|\band\b).*(\d+\s*=\s*\d+)', 
         "💀 Classic SQL injection attempt! Did you learn that from a 2005 tutorial? Your attack is now museum material."),
        (r'--\s*$|/\*.*\*/', 
         "🎭 SQL comments in a comment section? Meta! Your injection attempt is now ironically stored as... a comment."),
        (r'\bdrop\s+table\b', 
         "💣 DROP TABLE? Bold move! Unfortunately, your digital destruction attempt is now safely quarantined as text."),
        (r'\bload_file\b|into\s+outfile', 
         "📁 File system access attempt detected! Your hacking dreams are now filed under 'Epic Fails'."),
        (r'\bbenchmark\s*\(|sleep\s*\(', 
         "⏰ Timing attack? How quaint! The only thing sleeping here is your hacking skills."),
    ]
    
    # XSS patterns
    xss_patterns = [
        (r'<script[^>]*>.*?</script>', 
         "🚨 XSS attempt spotted! Your JavaScript dreams are now plain text nightmares."),
        (r'javascript:', 
         "⚡ JavaScript protocol detected! Your code execution fantasies are now safely neutered."),
        (r'on\w+\s*=', 
         "🎪 Event handler injection? Cute! Your onclick dreams are now plain text memes."),
        (r'<iframe[^>]*>', 
         "🖼️ Iframe injection? Trying to frame someone? Your attack is now framed... as text."),
        (r'<img[^>]*onerror', 
         "🖼️ Image onerror XSS? Classic! Your pixel-perfect attack is now perfectly pointless."),
        (r'alert\s*\(|confirm\s*\(|prompt\s*\(', 
         "📢 Alert box injection? The only alert here is that your hacking skills need work!"),
    ]
    
    # Command injection patterns
    cmd_patterns = [
        (r';\s*(cat|ls|pwd|whoami|id|uname)', 
         "💻 Command injection attempt! Your terminal dreams are now just terminal embarrassment."),
        (r'\|\s*(nc|netcat|wget|curl)', 
         "🌐 Network command detected! Your remote access attempt is now locally laughable."),
        (r'`[^`]*`|\$\([^)]*\)', 
         "🐚 Shell command substitution? Your bash skills are now just... trash."),
    ]
    
    # LDAP injection patterns
    ldap_patterns = [
        (r'\*\)\(|\)\(\*', 
         "🔍 LDAP injection detected! Your directory traversal is now just... lost."),
    ]
    
    # NoSQL injection patterns
    nosql_patterns = [
        (r'\$where|\$ne|\$gt|\$lt', 
         "🍃 NoSQL injection attempt! Your MongoDB mischief is now just... plain old text."),
    ]
    
    all_patterns = sql_patterns + xss_patterns + cmd_patterns + ldap_patterns + nosql_patterns
    
    for pattern, message in all_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
            return message
    
    # Generic suspicious patterns
    if len([c for c in text if c in "'\"`;(){}[]<>"]) > 5:
        return "🎯 Suspicious character overload! Your injection cocktail is now a text-only mocktail."
    
    return None

def validate_comment_input(text):
    """Minimal validation: allow raw text, only limit excessive size."""
    if not isinstance(text, str):
        return False, "Invalid comment input"
    if len(text) > 10000:
        return False, "Comment too long"
    return True, "Valid input"



@main_bp.route("/", methods=["GET", "POST"])
@limiter.limit("10 per minute; 100 per hour", methods=["POST"], error_message="Too many submissions. Please slow down.")
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
                    # Pre-validate file size before saving
                    f.seek(0, 2)  # Seek to end
                    file_size = f.tell()
                    f.seek(0)  # Reset to beginning
                    
                    if file_size > 10 * 1024 * 1024:  # 10MB hard limit
                        flash("File too large. Maximum size is 10MB to prevent system crashes.")
                    elif file_size < 100:  # Too small to be a valid image
                        flash("File too small to be a valid image.")
                    else:
                        # Additional check: read first few bytes to detect obvious bombs
                        f.seek(0)
                        header = f.read(1024)  # Read first 1KB
                        f.seek(0)
                        
                        # Check for suspicious patterns in header
                        if b'\x00' * 100 in header:  # Lots of null bytes
                            flash("File contains suspicious patterns and was rejected.")
                        else:
                            unique_name = f"{uuid.uuid4().hex}{ext}"
                            dest = os.path.join(current_app.config["UPLOAD_DIR"], unique_name)
                            f.save(dest)

                            ok, fmt, dims = verify_image(dest)
                    if not ok:
                        os.remove(dest)
                        flash("Image rejected due to suspicious or unsafe content (possible decompression bomb or invalid image).")
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
                # Detect injection attempts and show sarcastic message
                injection_message = detect_injection_attempts(text) if text else None
                
                # Store raw text using raw SQL
                try:
                    entry_id = insert_entry(text or None, image_filename)
                    if entry_id:
                        flash("Comment saved.")
                    else:
                        flash("Failed to save comment.")
                except Exception as e:
                    flash("Database error occurred while saving.")
                    current_app.logger.error(f"Database error: {str(e)}")
                
                if injection_message:
                    # Show sarcastic message for injection attempts
                    flash(injection_message, 'warning')
                    
            except Exception as e:
                flash("An error occurred while saving. Please try again.")
                current_app.logger.error(f"Database error: {str(e)}")
        else:
            flash("Submitted nothing? That's one way to avoid getting caught. Still a no.")

        return redirect(url_for("main.home"))

    try:
        # Always fetch all recent entries using raw SQL
        entries = get_recent_entries(100)
        total_count = get_total_entries_count()
                
    except Exception as e:
        current_app.logger.error(f"Error fetching entries: {str(e)}")
        entries = []
        total_count = 0
        flash("The digital archive is corrupted. Please try again later.")

    return render_template(
        "home.html",
        entries=entries,
        total_count=total_count,
        max_size_bytes=current_app.config.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024),
        allowed_exts=sorted(ALLOWED_EXTS),
        allowed_mimes=sorted(ALLOWED_MIME_TYPES),
    )

@main_bp.route("/uploads/<filename>")
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
    return render_template("429.html"), 429
