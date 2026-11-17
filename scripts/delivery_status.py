"""Keep preflight readiness, preview rendering and PowerPoint acceptance separate."""
import hashlib
from pathlib import Path
from office_runtime import verify_images

def assess(output, render_directory, count, evidence):
    result = {'deliverable': False, 'artifact_status': 'candidate',
              'powerpoint_validation_status': 'not_verified',
              'visual_review_status': 'pending', 'delivery_status': 'pending_render',
              'render_status': 'pending', 'render_error_code': None}
    if not evidence or evidence.get('status') != 'passed':
        result['render_status'] = (evidence or {}).get('status', 'pending')
        result['render_error_code'] = (evidence or {}).get('error_code', 'RENDER_EVIDENCE_MISSING')
        return result
    try:
        verify_images(render_directory, count)
    except (OSError, ValueError) as exc:
        result.update(render_status='failed', render_error_code='RENDER_OUTPUT_INVALID', render_detail=str(exc))
        return result
    result.update(render_status='passed', delivery_status='pending_powerpoint_validation')
    if (evidence.get('application') == 'Microsoft PowerPoint' and evidence.get('opened') is True
            and evidence.get('slide_count') == count
            and evidence.get('output_sha256') == hashlib.sha256(Path(output).read_bytes()).hexdigest()):
        result.update(powerpoint_validation_status='passed', delivery_status='pending_visual_review')
    return result


def exit_code(report, executing=False):
    if report['status'] == 'blocked':
        return 2
    if executing and not report.get('deliverable', False):
        return 3  # Candidate exists, but it is not accepted for delivery.
    return 0
