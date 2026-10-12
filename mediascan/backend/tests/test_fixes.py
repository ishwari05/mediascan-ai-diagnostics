import os
import io
import json
import pytest
import torch
import numpy as np
from PIL import Image
from flask_jwt_extended import create_access_token

from app import create_app
from database import db, User, Prediction, hash_password
from models.ai_models import model_manager, GradCAM, generate_gradcam, IMG_SIZE


@pytest.fixture(scope='module')
def app():
    # Setup test app
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })
    
    with app.app_context():
        db.create_all()
        # Seed test admin and standard user
        admin = User.query.filter_by(email='admin@mediascan.ai').first()
        if not admin:
            admin = User(
                name='Admin Tester',
                email='admin@mediascan.ai',
                password_hash=hash_password('Admin@123'),
                role='admin'
            )
            db.session.add(admin)
        
        user = User.query.filter_by(email='patient@mediascan.ai').first()
        if not user:
            user = User(
                name='Patient Tester',
                email='patient@mediascan.ai',
                password_hash=hash_password('Patient@123'),
                role='user'
            )
            db.session.add(user)
        
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_token(app):
    with app.app_context():
        user = User.query.filter_by(email='patient@mediascan.ai').first()
        return create_access_token(identity=str(user.id))


@pytest.fixture
def admin_token(app):
    with app.app_context():
        admin = User.query.filter_by(email='admin@mediascan.ai').first()
        return create_access_token(identity=str(admin.id))


def test_pdf_download_with_none_fields_and_plaintext_recommendation(app, client, user_token):
    """
    Test Bug 2 fix:
    PDF report generation must not crash when prediction has None fields
    and plain-text recommendation.
    """
    with app.app_context():
        user = User.query.filter_by(email='patient@mediascan.ai').first()
        pred = Prediction(
            user_id=user.id,
            session_id='test1234',
            # Intentionally set fields to None to test guard logic
            eye_prediction=None,
            eye_confidence=None,
            palm_prediction=None,
            palm_confidence=None,
            retina_prediction=None,
            retina_confidence=None,
            skin_prediction=None,
            skin_confidence=None,
            anemia_result=None,
            anemia_confidence=None,
            anemia_risk=None,
            diabetes_result=None,
            diabetes_confidence=None,
            diabetes_risk=None,
            dfu_result=None,
            dfu_confidence=None,
            dfu_risk=None,
            overall_risk=None,
            # Legacy plain-text recommendation (separated by bullets or plain string)
            recommendations='Maintain healthy hydration • Follow up with clinician in 30 days'
        )
        db.session.add(pred)
        db.session.commit()
        pred_id = pred.id

    # Request PDF download
    response = client.get(
        f'/api/reports/download/{pred_id}',
        headers={'Authorization': f'Bearer {user_token}'}
    )

    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert response.data.startswith(b'%PDF')


def test_admin_stats_counts_abnormal_dfu_cases(app, client, admin_token):
    """
    Test Bug 3 fix:
    Admin stats endpoint must count dfu_result with 'Abnormal(Ulcer)' instead of 'dfu_present'.
    """
    with app.app_context():
        user = User.query.filter_by(email='patient@mediascan.ai').first()
        pred = Prediction(
            user_id=user.id,
            session_id='dfu_test1',
            dfu_result='Abnormal(Ulcer)',
            dfu_confidence=98.5,
            dfu_risk='High',
            overall_risk='High',
            model_type='skin'
        )
        db.session.add(pred)
        db.session.commit()

    response = client.get(
        '/api/admin/stats',
        headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert 'dfu_cases' in data
    assert data['dfu_cases'] >= 1


def test_gradcam_hook_cleanup_and_leak_prevention():
    """
    Test Bug 1 fix:
    Target layer hooks must be cleaned up properly and hook count before
    and after calling GradCAM twice must remain identical.
    """
    model = model_manager.get_model('eye')
    if model is None:
        pytest.skip("Eye model not loaded")

    # MobileNet target layer is features[-1]
    target_layer = model.features[-1]

    initial_f_hooks = len(target_layer._forward_hooks)
    initial_b_hooks = len(target_layer._backward_hooks)

    dummy_input = torch.randn(1, 3, *IMG_SIZE)

    # First GradCAM call
    with GradCAM(model, target_layer) as cam:
        # Check hooks are present while inside context
        assert len(target_layer._forward_hooks) == initial_f_hooks + 1
        assert len(target_layer._backward_hooks) == initial_b_hooks + 1
        heatmap1 = cam.generate(dummy_input)
        assert heatmap1 is not None

    # Check hooks removed after first call
    assert len(target_layer._forward_hooks) == initial_f_hooks
    assert len(target_layer._backward_hooks) == initial_b_hooks

    # Second GradCAM call
    with GradCAM(model, target_layer) as cam:
        assert len(target_layer._forward_hooks) == initial_f_hooks + 1
        assert len(target_layer._backward_hooks) == initial_b_hooks + 1
        heatmap2 = cam.generate(dummy_input)
        assert heatmap2 is not None

    # Check hooks removed after second call
    assert len(target_layer._forward_hooks) == initial_f_hooks
    assert len(target_layer._backward_hooks) == initial_b_hooks


def test_generate_gradcam_helper_leaves_no_lingering_hooks(tmp_path):
    """
    Test generate_gradcam high-level function hook cleanup twice.
    """
    model = model_manager.get_model('eye')
    if model is None:
        pytest.skip("Eye model not loaded")

    target_layer = model.features[-1]
    initial_f_hooks = len(target_layer._forward_hooks)
    initial_b_hooks = len(target_layer._backward_hooks)

    # Create dummy image
    test_img_path = str(tmp_path / "test_input.png")
    test_out_path1 = str(tmp_path / "test_out1.png")
    test_out_path2 = str(tmp_path / "test_out2.png")
    
    img = Image.new('RGB', IMG_SIZE, color=(128, 128, 128))
    img.save(test_img_path)

    dummy_tensor = torch.randn(1, 3, *IMG_SIZE)

    # Call generate_gradcam twice
    out1 = generate_gradcam(model, dummy_tensor, test_img_path, test_out_path1, 'eye')
    assert os.path.exists(out1)
    assert len(target_layer._forward_hooks) == initial_f_hooks
    assert len(target_layer._backward_hooks) == initial_b_hooks

    out2 = generate_gradcam(model, dummy_tensor, test_img_path, test_out_path2, 'eye')
    assert os.path.exists(out2)
    assert len(target_layer._forward_hooks) == initial_f_hooks
    assert len(target_layer._backward_hooks) == initial_b_hooks


# ─── Task 2: PDF imagery tests ────────────────────────────────────────────────

def _make_tiny_png(path):
    """Write a 10×10 RGB PNG to *path* using only stdlib + PIL."""
    from PIL import Image
    img = Image.new('RGB', (10, 10), color=(100, 150, 200))
    img.save(path, 'PNG')


def test_pdf_download_with_images(app, client, user_token, tmp_path):
    """
    Task 2: PDF with valid scan and GradCAM images must return HTTP 200 and
    a valid %PDF payload.  Images are written to the app UPLOAD_FOLDER so the
    sandboxed path resolver can find them.
    """
    with app.app_context():
        upload_folder = app.config.get('UPLOAD_FOLDER', str(tmp_path))
        # Create real image files inside the upload folder
        eye_dir = os.path.join(upload_folder, 'eye')
        gcam_dir = os.path.join(upload_folder, 'gradcam')
        os.makedirs(eye_dir, exist_ok=True)
        os.makedirs(gcam_dir, exist_ok=True)

        eye_img_path  = os.path.join(eye_dir,  'test_eye.png')
        gcam_img_path = os.path.join(gcam_dir, 'test_eye_gradcam.png')
        _make_tiny_png(eye_img_path)
        _make_tiny_png(gcam_img_path)

        user = User.query.filter_by(email='patient@mediascan.ai').first()
        pred = Prediction(
            user_id=user.id,
            session_id='imgtest01',
            eye_image_path=eye_img_path,
            eye_gradcam_path=gcam_img_path,
            eye_prediction='Non-Anemic',
            eye_confidence=87.5,
            anemia_result='Non-Anemic',
            anemia_confidence=87.5,
            anemia_risk='low',
            overall_risk='low',
            model_type='eye',
            recommendations='["Stay hydrated", "Follow up in 3 months"]',
        )
        db.session.add(pred)
        db.session.commit()
        pred_id = pred.id

    response = client.get(
        f'/api/reports/download/{pred_id}',
        headers={'Authorization': f'Bearer {user_token}'},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.mimetype == 'application/pdf'
    assert response.data.startswith(b'%PDF'), "Response does not begin with %PDF"


def test_pdf_download_with_missing_images(app, client, user_token):
    """
    Task 2: PDF where image paths are set but the files do not exist must NOT
    crash; it must still return HTTP 200 with a valid %PDF payload (images
    replaced by 'Image unavailable' placeholders).
    """
    with app.app_context():
        user = User.query.filter_by(email='patient@mediascan.ai').first()
        pred = Prediction(
            user_id=user.id,
            session_id='imgtest02',
            # Paths that reference non-existent files
            eye_image_path='eye/does_not_exist.png',
            eye_gradcam_path='gradcam/does_not_exist_gcam.png',
            eye_prediction='Anemic',
            eye_confidence=91.2,
            anemia_result='Anemic',
            anemia_confidence=91.2,
            anemia_risk='high',
            overall_risk='high',
            model_type='eye',
        )
        db.session.add(pred)
        db.session.commit()
        pred_id = pred.id

    response = client.get(
        f'/api/reports/download/{pred_id}',
        headers={'Authorization': f'Bearer {user_token}'},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.mimetype == 'application/pdf'
    assert response.data.startswith(b'%PDF'), "Response does not begin with %PDF"
