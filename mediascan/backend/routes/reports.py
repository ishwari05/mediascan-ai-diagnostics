"""
Reports Routes for MediScan AI
Handles PDF report generation for diagnostic results.

Changes (Task 2):
- Embeds scan images and GradCAM heatmaps side-by-side via ReportLab RLImage.
- Path resolution is sandboxed to the uploads directory (no traversal).
- Missing images are replaced with an "Image unavailable" placeholder text.
- Multi-scan predictions show one row per modality that was actually scanned.
- Confidences of unscanned modalities show "N/A" instead of "0.0%".
- Added clinical disclaimer and doctor signature block.
"""

from flask import Blueprint, send_file, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import io
import json
from datetime import datetime
from typing import Optional

from database import Prediction, User

reports_bp = Blueprint('reports', __name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_image_path(upload_folder: str, raw_path: Optional[str]) -> Optional[str]:
    """
    Resolve *raw_path* to an absolute path that is guaranteed to live inside
    *upload_folder*.  Returns None if the file is missing or outside the
    sandbox.
    """
    if not raw_path:
        return None
    # raw_path may be relative ("eye/abc.png") or absolute
    if os.path.isabs(raw_path):
        abs_path = os.path.normpath(raw_path)
    else:
        abs_path = os.path.normpath(os.path.join(upload_folder, raw_path))

    # Sandbox check
    upload_real = os.path.realpath(upload_folder)
    if not os.path.realpath(abs_path).startswith(upload_real + os.sep) and \
            os.path.realpath(abs_path) != upload_real:
        return None

    return abs_path if os.path.isfile(abs_path) else None


def _rl_image_or_placeholder(path: Optional[str], width, height, styles):
    """
    Return a ReportLab RLImage scaled to *width* × *height* if *path* is
    valid, otherwise a plain Paragraph reading "Image unavailable".
    """
    from reportlab.platypus import Image as RLImage, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle

    if path:
        try:
            img = RLImage(path)
            # Scale preserving aspect ratio, capped at requested dims
            iw, ih = img.imageWidth, img.imageHeight
            if iw and ih:
                ratio = min(width / iw, height / ih)
                img.drawWidth = iw * ratio
                img.drawHeight = ih * ratio
            return img
        except Exception:
            pass  # fall through to placeholder

    placeholder_style = ParagraphStyle(
        'ImgPlaceholder',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1,
        borderColor=colors.HexColor('#e2e8f0'),
        borderWidth=1,
        borderPadding=12,
    )
    return Paragraph("Image unavailable", placeholder_style)


def _fmt_conf(value) -> str:
    """Format confidence or return 'N/A' for None / zero when not scanned."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


# ─── Route ────────────────────────────────────────────────────────────────────

@reports_bp.route('/download/<int:pred_id>', methods=['GET'])
@jwt_required()
def download_report(pred_id):
    user_id = int(get_jwt_identity())
    pred = Prediction.query.get_or_404(pred_id)
    user = User.query.get(user_id)

    if pred.user_id != user_id and user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle, HRFlowable,
        )
        from reportlab.lib.units import inch

        UPLOAD_FOLDER = current_app.config.get('UPLOAD_FOLDER', '')
        PAGE_W = letter[0] - 144  # usable width (72pt margins each side)
        IMG_W  = PAGE_W / 2 - 6   # each image half-width minus gutter
        IMG_H  = 1.8 * inch

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter,
            rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18,
        )
        styles = getSampleStyleSheet()

        # ── Custom styles ──────────────────────────────────────────────────
        title_style = ParagraphStyle(
            'TitleStyle', parent=styles['Heading1'],
            fontSize=26, textColor=colors.HexColor("#0891b2"),
            alignment=1, spaceAfter=12,
        )
        section_style = ParagraphStyle(
            'SectionStyle', parent=styles['Heading2'],
            fontSize=14, textColor=colors.black,
            spaceBefore=14, spaceAfter=8,
        )
        label_style = ParagraphStyle(
            'LabelStyle', parent=styles['Normal'],
            fontSize=8, textColor=colors.HexColor('#64748b'),
            alignment=1, spaceAfter=2,
        )
        disclaimer_style = ParagraphStyle(
            'Disclaimer', parent=styles['Normal'],
            fontSize=8, textColor=colors.HexColor('#64748b'), alignment=1,
        )

        elements = []

        # ── Header ────────────────────────────────────────────────────────
        elements.append(Paragraph("MediScan AI Diagnostic Report", title_style))
        elements.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            styles['Normal'],
        ))
        elements.append(Spacer(1, 0.2 * inch))

        # ── Patient info table ─────────────────────────────────────────────
        patient_data = [
            ['Patient Name:', user.name if user and user.name else 'N/A',
             'Report ID:', f"MS-{(pred.session_id or 'UNKNOWN')[:8].upper()}"],
            ['Patient Email:', user.email if user and user.email else 'N/A',
             'Scan Date:', pred.created_at.strftime('%Y-%m-%d') if pred.created_at else datetime.now().strftime('%Y-%m-%d')],
            ['Age / Gender:',
             f"{(user.age if user else None) or 'N/A'} / {(user.gender if user else None) or 'N/A'}",
             'Overall Risk:', (pred.overall_risk or 'UNKNOWN').upper()],
        ]
        t = Table(patient_data, colWidths=[1.2 * inch, 2 * inch, 1.2 * inch, 1.8 * inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (3, 2), (3, 2),
             colors.red if (pred.overall_risk or '').lower() == 'high' else colors.green),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.3 * inch))

        # ── Per-modality image rows ────────────────────────────────────────
        MODALITIES = [
            ('eye',    'Eye Conjunctiva',  pred.eye_image_path,    pred.eye_gradcam_path,    pred.eye_prediction,    pred.eye_confidence),
            ('palm',   'Palm Skin',        pred.palm_image_path,   pred.palm_gradcam_path,   pred.palm_prediction,   pred.palm_confidence),
            ('retina', 'Retinal Fundus',   pred.retina_image_path, pred.retina_gradcam_path, pred.retina_prediction, pred.retina_confidence),
            ('skin',   'Skin / DFU',       pred.skin_image_path,   pred.skin_gradcam_path,   pred.skin_prediction,   pred.skin_confidence),
        ]

        scanned_modalities = [m for m in MODALITIES if m[2] or m[4]]  # has image path OR prediction

        if scanned_modalities:
            elements.append(Paragraph("Scan Images & GradCAM Heatmaps", section_style))

            for _, label, img_path, gcam_path, prediction, confidence in scanned_modalities:
                safe_img  = _safe_image_path(UPLOAD_FOLDER, img_path)
                safe_gcam = _safe_image_path(UPLOAD_FOLDER, gcam_path)

                scan_img  = _rl_image_or_placeholder(safe_img,  IMG_W, IMG_H, styles)
                gcam_img  = _rl_image_or_placeholder(safe_gcam, IMG_W, IMG_H, styles)

                img_table = Table(
                    [[scan_img, gcam_img]],
                    colWidths=[IMG_W + 6, IMG_W + 6],
                )
                img_table.setStyle(TableStyle([
                    ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING',(0, 0), (-1, -1), 3),
                ]))

                # Labels row
                lbl_table = Table(
                    [[Paragraph(f"{label} — Original Scan", label_style),
                      Paragraph(f"{label} — GradCAM Heatmap", label_style)]],
                    colWidths=[IMG_W + 6, IMG_W + 6],
                )
                lbl_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('LEFTPADDING',  (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ]))

                elements.append(img_table)
                elements.append(lbl_table)

                if prediction:
                    conf_str = _fmt_conf(confidence)
                    elements.append(Paragraph(
                        f"<b>{label}:</b> {prediction} ({conf_str})",
                        styles['Normal'],
                    ))
                elements.append(Spacer(1, 0.15 * inch))

        # ── Anemia section ────────────────────────────────────────────────
        elements.append(Paragraph("I. Anemia Screening Results", section_style))
        # Show N/A for confidences that weren't scanned (no image path stored)
        eye_conf  = _fmt_conf(pred.eye_confidence)  if pred.eye_image_path  else "N/A"
        palm_conf = _fmt_conf(pred.palm_confidence) if pred.palm_image_path else "N/A"

        anemia_data = [
            ['Component', 'Visual Prediction', 'Confidence', 'Status'],
            ['Eye Conjunctiva', pred.eye_prediction or 'Not Scanned',   eye_conf,  'CHECK'],
            ['Palm Skin',       pred.palm_prediction or 'Not Scanned',  palm_conf, 'CHECK'],
            ['FUSED DIAGNOSIS',
             (pred.anemia_result or 'Not Scanned').upper(),
             _fmt_conf(pred.anemia_confidence),
             (pred.anemia_risk or 'none').upper()],
        ]
        at = Table(anemia_data, colWidths=[1.8 * inch, 1.8 * inch, 1.2 * inch, 1.2 * inch])
        at.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR',  (1, 3), (1, 3),
             colors.red if pred.anemia_result == 'Anemic' else colors.green),
            ('FONTNAME',   (0, 3), (-1, 3), 'Helvetica-Bold'),
        ]))
        elements.append(at)

        # ── Diabetes section ──────────────────────────────────────────────
        elements.append(Paragraph("II. Diabetes Screening Results", section_style))
        retina_conf = _fmt_conf(pred.retina_confidence) if pred.retina_image_path else "N/A"
        skin_conf   = _fmt_conf(pred.skin_confidence)   if pred.skin_image_path   else "N/A"

        diabetes_data = [
            ['Component', 'Visual Prediction', 'Confidence', 'Status'],
            ['Retinal Fundus', pred.retina_prediction or 'Not Scanned', retina_conf, 'CHECK'],
            ['Skin/DFU Check', pred.skin_prediction   or 'Not Scanned', skin_conf,   'CHECK'],
            ['FUSED DIAGNOSIS',
             (pred.diabetes_result or 'Not Scanned').upper(),
             _fmt_conf(pred.diabetes_confidence),
             (pred.diabetes_risk or 'none').upper()],
        ]
        dt = Table(diabetes_data, colWidths=[1.8 * inch, 1.8 * inch, 1.2 * inch, 1.2 * inch])
        dt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR',  (1, 3), (1, 3),
             colors.red if pred.diabetes_result == 'Diabetic' else colors.green),
            ('FONTNAME',   (0, 3), (-1, 3), 'Helvetica-Bold'),
        ]))
        elements.append(dt)

        # ── Recommendations ───────────────────────────────────────────────
        elements.append(Paragraph("III. Personalized Recommendations", section_style))
        recs_list = []
        if pred.recommendations:
            try:
                decoded = json.loads(pred.recommendations)
                recs_list = decoded if isinstance(decoded, list) else [str(decoded)]
            except (json.JSONDecodeError, TypeError):
                recs_list = [r.strip() for r in pred.recommendations.split('•') if r.strip()]
                if not recs_list:
                    recs_list = [pred.recommendations]

        for r in recs_list:
            elements.append(Paragraph(f"• {r}", styles['Normal']))
            elements.append(Spacer(1, 0.05 * inch))

        # ── Clinical disclaimer ───────────────────────────────────────────
        elements.append(Spacer(1, 0.4 * inch))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0')))
        elements.append(Spacer(1, 0.15 * inch))

        disclaimer_text = (
            "<b>Clinical Disclaimer:</b> This report is generated by an AI screening tool "
            "and is intended as a <b>screening aid only</b>. It does <b>not</b> constitute "
            "a medical diagnosis, replace clinical evaluation, or substitute for the advice "
            "of a qualified healthcare professional. Please consult a licensed doctor before "
            "making any health decisions."
        )
        elements.append(Paragraph(disclaimer_text, disclaimer_style))
        elements.append(Spacer(1, 0.4 * inch))

        # ── Signature block ───────────────────────────────────────────────
        sig_data = [
            ['Doctor Name:', '_' * 30, 'Date:', datetime.now().strftime('%Y-%m-%d')],
            ['Signature:',   '_' * 30, '',      ''],
        ]
        sig_table = Table(sig_data, colWidths=[1.0 * inch, 2.5 * inch, 0.7 * inch, 1.5 * inch])
        sig_table.setStyle(TableStyle([
            ('FONTNAME',      (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME',      (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ]))
        elements.append(sig_table)

        # ── Build ─────────────────────────────────────────────────────────
        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"MediScan_Report_{pred_id}.pdf",
            mimetype='application/pdf',
        )

    except Exception as e:
        return jsonify({
            'error': f'PDF Generation failed: {str(e)}',
            'plain_text_report': pred.to_dict(),
        }), 500
