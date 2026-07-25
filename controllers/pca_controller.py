from flask import Blueprint, jsonify

pca_bp = Blueprint('pca_controller', __name__, url_prefix='/api/pca')

@pca_bp.route('/analyze', methods=['POST'])
def analyze_color():
    return jsonify({'message': 'PCA 膚色分析功能開發中...'})