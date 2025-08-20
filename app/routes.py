import os, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, session, abort
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
from .models import db, Comment, Entry
from .limits import limiter
import secrets
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
                # Detect injection attempts and show sarcastic message
                injection_message = detect_injection_attempts(text) if text else None
                
                # Store raw text; keep filenames validated by image pipeline
                entry = Entry(text=text or None, image_filename=image_filename)
                db.session.add(entry)
                db.session.commit()
                
                if injection_message:
                    # Show sarcastic message for injection attempts
                    flash(injection_message, 'warning')
                elif text and not image_filename:
                    flash("Comment saved.")
                    
            except Exception as e:
                flash("An error occurred while saving. Please try again.")
                db.session.rollback()
                current_app.logger.error(f"Database error: {str(e)}")
        else:
            flash("Submitted nothing? That's one way to avoid getting caught. Still a no.")

        return redirect(url_for("main.home"))

    try:
        # Always fetch all recent entries - search will be done client-side
        entries = Entry.query.order_by(Entry.id.desc()).limit(100).all()
                
    except Exception as e:
        current_app.logger.error(f"Error fetching entries: {str(e)}")
        entries = []
        flash("The digital archive is corrupted. Please try again later.")

    return render_template(
        "home.html",
        entries=entries,
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
