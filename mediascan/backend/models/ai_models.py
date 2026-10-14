import os
import numpy as np
import logging
import threading
from PIL import Image, ImageDraw
import json
import torch
import torch.nn as nn
from torchvision import models, transforms
import cv2

# Set absolute path for models directory to ensure it's found from any working directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODEL_DIR = os.path.join(BASE_DIR, "SB_Project", "codebase", "outputs", "models")
logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
CLASSES = {
    'eye':    ['anemia', 'non_anemia'],
    'palm':   ['anemia', 'non_anemia'],
    'retina': ['Mild', 'Moderate', 'No_DR', 'Proliferate_DR', 'Severe'],
    'skin':   ['Abnormal(Ulcer)', 'Normal(Healthy skin)']
}

IMG_SIZE = (224, 224)
NORMALIZE_MEAN = [0.485, 0.456, 0.406]
NORMALIZE_STD  = [0.229, 0.224, 0.225]

# ─── Model Factory ────────────────────────────────────────────────────────────
def build_mobilenet_v2(num_classes):
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.2),
        nn.Linear(in_features, num_classes),
    )
    return model

def build_resnet50(num_classes):
    model = models.resnet50(weights=None)
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, num_classes),
    )
    return model

# ─── Model Manager (Singleton) ────────────────────────────────────────────────
class ModelManager:
    _instance = None
    _models = {}
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_models(self, models_folder=None):
        """Load all .pth models from disk using project-relative paths."""
        try:
            model_configs = {
                'eye':    {'path': os.path.join(MODEL_DIR, 'Anemia_eye_mobilenet.pth'), 'arch': 'mobilenet'},
                'retina': {'path': os.path.join(MODEL_DIR, 'diabetes_eye_resnet50.pth'),  'arch': 'resnet50'},
                'skin':   {'path': os.path.join(MODEL_DIR, 'diabetes_skin_resnet50.pth'), 'arch': 'resnet50'},
                'palm':   {'path': os.path.join(MODEL_DIR, 'Anemia_skin_resnet50 .pth'), 'arch': 'resnet50'}
            }
            print(f"[ModelManager] Initializing from: {MODEL_DIR}")
        except Exception as e:
            logger.error(f"Failed to resolve model directory: {e}")
            return

        for key, cfg in model_configs.items():
            path = cfg['path']
            if os.path.exists(path):
                try:
                    num_classes = len(CLASSES[key])
                    if cfg['arch'] == 'mobilenet':
                        model = build_mobilenet_v2(num_classes)
                    else:
                        model = build_resnet50(num_classes)
                    
                    state_dict = torch.load(path, map_location=self._device)
                    model.load_state_dict(state_dict)
                    model.to(self._device)
                    model.eval()
                    self._models[key] = model
                    logger.info(f"[OK] Loaded {key} ({cfg['arch']}) model")
                    print(f"✅ [OK] Loaded {key} model")
                except Exception as e:
                    logger.error(f"[FAIL] Could not load {key} model: {e}")
                    print(f"❌ [FAIL] Could not load {key} model: {e}")
            else:
                logger.error(f"[CRITICAL] Model file not found: {path}")
                print(f"❌ [CRITICAL] Model file not found: {path}")

    def get_model(self, model_type):
        return self._models.get(model_type)

model_manager = ModelManager()

# ─── Preprocessing ──────────────────────────────────────────────────────────
inference_transforms = transforms.Compose([
    transforms.Resize(IMG_SIZE),
    transforms.ToTensor(),
    transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD)
])

def preprocess_image(image_path):
    img = Image.open(image_path).convert('RGB')
    tensor = inference_transforms(img).unsqueeze(0)
    return tensor.to(model_manager._device)

def validate_image(image_path):
    try:
        img = Image.open(image_path)
        if img.format not in ['JPEG', 'PNG', 'WEBP', 'BMP']:
            return False, f"Unsupported format: {img.format}"
        img.verify()
        return True, ""
    except Exception as e:
        return False, str(e)

# ─── GradCAM (PyTorch Implementation) ─────────────────────────────────────────
_gradcam_lock = threading.Lock()

class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self.handles = []

    def hook_layers(self):
        self.remove_hooks()
        def forward_hook(module, input, output):
            self.activations = output
        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0]
        
        h_f = self.target_layer.register_forward_hook(forward_hook)
        h_b = self.target_layer.register_full_backward_hook(backward_hook)
        self.handles = [h_f, h_b]

    def remove_hooks(self):
        for h in self.handles:
            try:
                h.remove()
            except Exception:
                pass
        self.handles = []
        self.gradients = None
        self.activations = None

    def __enter__(self):
        self.hook_layers()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.remove_hooks()

    def generate(self, input_tensor, class_idx=None):
        need_cleanup = False
        if not self.handles:
            self.hook_layers()
            need_cleanup = True
        try:
            self.model.zero_grad()
            with torch.enable_grad():
                output = self.model(input_tensor)
                if class_idx is None:
                    class_idx = torch.argmax(output)
                
                output[0, class_idx].backward()
            
            if self.gradients is None or self.activations is None:
                raise RuntimeError("GradCAM hooks failed to capture gradients/activations.")

            gradients = self.gradients.detach().cpu().data.numpy()[0]
            activations = self.activations.detach().cpu().data.numpy()[0]
            
            weights = np.mean(gradients, axis=(1, 2))
            cam = np.zeros(activations.shape[1:], dtype=np.float32)
            
            for i, w in enumerate(weights):
                cam += w * activations[i, :, :]
                
            cam = np.maximum(cam, 0)
            cam = cv2.resize(cam, IMG_SIZE)
            cam = cam - np.min(cam)
            cam = cam / (np.max(cam) + 1e-10)
            return cam
        finally:
            self.model.zero_grad()
            if need_cleanup:
                self.remove_hooks()
            else:
                self.gradients = None
                self.activations = None

def generate_gradcam(model, input_tensor, image_path, output_path, model_type):
    try:
        if 'resnet' in str(type(model)).lower():
            target_layer = model.layer4[-1]
        else: # MobileNet
            target_layer = model.features[-1]
            
        with _gradcam_lock:
            with GradCAM(model, target_layer) as cam_gen:
                heatmap = cam_gen.generate(input_tensor)
        
        img = cv2.imread(image_path)
        img = cv2.resize(img, IMG_SIZE)
        heatmap_color = cv2.applyColorMap(np.uint8(255 * heatmap), cv2.COLORMAP_JET)
        
        superimposed = cv2.addWeighted(img, 0.6, heatmap_color, 0.4, 0)
        cv2.imwrite(output_path, superimposed)
        return output_path
    except Exception as e:
        logger.error(f"GradCAM failed: {e}")
        return _generate_demo_gradcam(image_path, output_path)

def _generate_demo_gradcam(image_path, output_path):
    try:
        img = Image.open(image_path).convert('RGB').resize(IMG_SIZE)
        overlay = Image.new('RGBA', IMG_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        cx, cy = 112, 112
        for r in range(60, 10, -10):
            alpha = int(100 * (1 - r/60))
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 120, 0, alpha))
        img.paste(overlay, (0,0), overlay)
        img.save(output_path)
        return output_path
    except: return None

# ─── Prediction Logic ──────────────────────────────────────────────────────────
def _predict(model_type, image_path, gradcam_output_path=None):
    valid, err = validate_image(image_path)
    if not valid: return {'error': err, 'status': 'failed'}
    
    model = model_manager.get_model(model_type)
    if model is None:
        logger.error(f"❌ Subsystem failure: {model_type} model not available. Demo mode disabled.")
        return {'error': f"Neural analysis subsystem for {model_type} is offline. Please contact admin.", 'status': 'failed'}
        
    try:
        input_tensor = preprocess_image(image_path)
        with torch.no_grad():
            outputs = model(input_tensor)
            probs = torch.softmax(outputs, dim=1)[0]
        
        probs_np = probs.cpu().numpy()
        idx = int(np.argmax(probs_np))
        prediction = CLASSES[model_type][idx]
        confidence = float(probs_np[idx]) * 100
        
        res = {
            'prediction': prediction,
            'confidence': round(confidence, 2),
            'probabilities': {CLASSES[model_type][i]: round(float(probs_np[i])*100, 2) for i in range(len(CLASSES[model_type]))},
            'demo_mode': False,
            'status': 'success',
            'model_type': model_type
        }
        
        if gradcam_output_path:
            res['gradcam_path'] = generate_gradcam(model, input_tensor, image_path, gradcam_output_path, model_type)
            
        return res
    except Exception as e:
        logger.error(f"Inference failed for {model_type}: {e}")
        return {'error': str(e), 'status': 'failed'}

def _demo_predict(model_type, gradcam_output_path, image_path):
    import random
    is_positive = random.random() > 0.6
    conf = random.uniform(75, 98)
    res = {
        'prediction': CLASSES[model_type][0] if is_positive else CLASSES[model_type][1],
        'confidence': round(conf, 2),
        'probabilities': {CLASSES[model_type][i]: round(conf/len(CLASSES[model_type]) if i==0 else (100-conf)/(len(CLASSES[model_type])-1),2) for i in range(len(CLASSES[model_type]))},
        'demo_mode': True,
        'status': 'success',
        'model_type': model_type
    }
    if gradcam_output_path: res['gradcam_path'] = _generate_demo_gradcam(image_path, gradcam_output_path)
    return res

# Facade
def predict_eye_anemia(p, g=None): return _predict('eye', p, g)
def predict_palm_anemia(p, g=None): return _predict('palm', p, g)
def predict_retina_diabetes(p, g=None): return _predict('retina', p, g)
def predict_skin_dfu(p, g=None): return _predict('skin', p, g)

# ─── Clinical Domain Identification (IMPROVED ROBUSTNESS) ────────────────────
def identify_domain(image_path):
    """
    Identifies scan types by running all models and applying structural tie-breaking.
    """
    try:
        # 1. LOAD IMAGE & BASIC HEURISTICS
        img = cv2.imread(image_path)
        if img is None: return 'eye'
        
        h, w = img.shape[:2]
        
        # Enhanced Vignette Check: If ANY edge/corner is black, it's likely a clinical scan.
        c = 20
        edge_blocks = [
            img[:c, :c], img[:c, -c:], img[-c:, :c], img[-c:, -c:], # Corners
            img[h//2-c:h//2+c, :c], img[h//2-c:h//2+c, -c:],       # Sides
            img[:c, w//2-c:w//2+c], img[-c:, w//2-c:w//2+c]        # Top/Bottom
        ]
        block_averages = [np.mean(b) for b in edge_blocks]
        min_edge_val = min(block_averages)
        
        # If any significant edge block is dark (< 50), it's a vignette image (Retina/Eye)
        is_vignette = min_edge_val < 50
        
        # Color & Circularity Features
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        skin_mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
        skin_ratio = np.count_nonzero(skin_mask) / (h*w)
        
        # 2. RUN ALL FOUR MODELS (Confidence Sweep)
        domains = ['retina', 'eye', 'palm', 'skin']
        confidences = {}
        
        for d in domains:
            # EXCLUSION: Vignetted images are never Skin/Palm
            if is_vignette and d in ['skin', 'palm']:
                continue
            
            res = _predict(d, image_path)
            if res.get('status') == 'success':
                conf = res.get('confidence', 0)
                
                # Weighting
                if d == 'retina' and is_vignette:
                    conf += 15 # Strong clinical signal boost
                if d == 'eye' and is_vignette:
                    conf *= 0.6 # Eye scans are usually bright crops
                    
                confidences[d] = conf

        if not confidences:
            return 'retina' if is_vignette else 'eye'

        # 3. SELECT WINNER
        sorted_conf = sorted(confidences.items(), key=lambda x: x[1], reverse=True)
        best_domain, best_conf = sorted_conf[0]
        
        # THE ULTIMATE TIE-BREAKER
        # If dark edges exist, Retina always wins against Eye if it has any decent confidence.
        if is_vignette and confidences.get('retina', 0) > 40:
            return 'retina'
            
        logger.info(f"Auto-Detect Final: {best_domain.upper()} ({best_conf:.2f}%) [min_edge: {min_edge_val:.1f}]")
        return best_domain

    except Exception as e:
        logger.error(f"Auto-Detection Pipeline Crash: {e}")
        return 'eye' # Safe fallback to standard eye model

def predict_auto(image_path, gradcam_output_path=None):
    detected_domain = identify_domain(image_path)
    res = _predict(detected_domain, image_path, gradcam_output_path)
    res['detected_domain'] = detected_domain
    return res

# ─── Fusion Logic (Fixed Thresholds) ──────────────────────────────────────────
def fuse_anemia_predictions(eye, palm):
    if eye.get('status') == 'failed' or palm.get('status') == 'failed':
        return {'result': 'Inconclusive', 'confidence': 0.0, 'risk': 'Unknown'}

    e_p = eye.get('probabilities', {}).get('anemia')
    p_p = palm.get('probabilities', {}).get('anemia')
    
    if e_p is None and p_p is None:
        return {'result': 'Not Scanned', 'confidence': 0.0, 'risk': 'none'}
        
    if e_p is not None and p_p is not None:
        fused = (float(e_p)/100 * 0.55) + (float(p_p)/100 * 0.45)
    elif e_p is not None:
        fused = float(e_p)/100
    else:
        fused = float(p_p)/100

    is_anemic = fused >= 0.5
    conf = fused if is_anemic else (1 - fused)
    risk = 'High' if fused > 0.8 else ('Medium' if fused > 0.4 else 'Low')
    return {'result': 'Anemic' if is_anemic else 'Non-Anemic', 'confidence': round(conf * 100, 2), 'risk': risk}

def fuse_diabetes_predictions(retina, skin):
    if retina.get('status') == 'failed' or skin.get('status') == 'failed':
        return {'result': 'Inconclusive', 'confidence': 0.0, 'risk': 'Unknown'}

    no_dr_p = retina.get('probabilities', {}).get('No_DR')
    is_diabetic_r = (1 - float(no_dr_p)/100) if no_dr_p is not None else None
    
    abnormal_p = skin.get('probabilities', {}).get('Abnormal(Ulcer)')
    is_diabetic_s = float(abnormal_p)/100 if abnormal_p is not None else None
    
    if is_diabetic_r is None and is_diabetic_s is None:
        return {'result': 'Not Scanned', 'confidence': 0.0, 'risk': 'none'}

    if is_diabetic_r is not None and is_diabetic_s is not None:
        fused = (is_diabetic_r * 0.60) + (is_diabetic_s * 0.40)
    elif is_diabetic_r is not None:
        fused = is_diabetic_r
    else:
        fused = is_diabetic_s

    is_diabetic = fused >= 0.5
    conf = fused if is_diabetic else (1 - fused)
    risk = 'High' if fused > 0.75 else ('Medium' if fused > 0.35 else 'Low')
    return {'result': 'Diabetic' if is_diabetic else 'Non-Diabetic', 'confidence': round(conf * 100, 2), 'risk': risk}

def compute_overall_risk(a_risk, d_risk):
    order = {'High': 3, 'Medium': 2, 'Low': 1}
    max_val = max(order.get(a_risk, 1), order.get(d_risk, 1))
    return [k for k, v in order.items() if v == max_val][0]

def generate_recommendations(anemia, diabetes, skin_res=None):
    recs = []
    if anemia.get('result') == 'Anemic':
        recs.append("⚠️ Anemia markers detected. Consult a haematologist for a Full Blood Count (FBC) test.")
    else:
        recs.append("✅ Hemoglobin levels appear normal based on visual analysis.")
        
    if diabetes.get('result') == 'Diabetic':
        recs.append("⚠️ Diabetic markers detected. Schedule an HbA1c test to confirm blood sugar levels.")
    else:
        recs.append("✅ Retina/Skin analysis shows low risk indicators for diabetes.")
        
    recs.append("⚕️ This AI screening tool is not a substitute for a clinical diagnosis. Consult a physician.")
    return recs
