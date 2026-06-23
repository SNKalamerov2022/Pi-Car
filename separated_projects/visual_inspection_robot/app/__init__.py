from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Database creation & Seeding
    with app.app_context():
        db.create_all()
        
        # Seed missions table with Zadanie 19 visual inspection loops (Presets)
        from app.models import Mission
        # Clear existing to ensure clean re-seeding
        Mission.query.delete()
        default_missions = [
            Mission(name="Preset 1 - Single Object", description="Track path, drive for 2.5s on object detection, photo, then stop.", num_checkpoints=1),
            Mission(name="Preset 2 - Dual Object", description="First target 2.5s, photo, turn left, drive 1.0s, photo, then stop.", num_checkpoints=2)
        ]
        for m in default_missions:
            db.session.add(m)
        db.session.commit()

    return app