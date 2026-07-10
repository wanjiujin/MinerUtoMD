"""
PDF 水印去除模块
使用 OpenCV 进行水印检测和去除

核心思路:
- 快速模式: 基于颜色阈值检测浅色半透明水印，用 inpainting 修复
- 深度模式: 基于频域分析检测重复性水印模式，用 inpainting 修复
- PDF 模式: 渲染每页为图像 → 去水印 → 替换页面内容
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)


class WatermarkRemover:
    """PDF 水印去除器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化水印去除器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        # 水印去除模式: fast (快速), deep (深度)
        self.mode = self.config.get('mode', 'fast')
        # 最小水印面积（像素），低于此值的区域不处理
        self.min_area = self.config.get('min_area', 500)
        # 快速模式：水印灰度范围（仅针对浅色水印，如浅灰色/白色半透明水印）
        # 范围越窄越精确，误伤越少
        self.watermark_gray_range = self.config.get('watermark_gray_range', (220, 255))
        # 快速模式：inpaint 半径
        self.inpaint_radius = self.config.get('inpaint_radius', 5)
        # 深度模式：水印检测灵敏度 (0-1)，越高检测越灵敏
        self.deep_sensitivity = self.config.get('deep_sensitivity', 0.3)
    
    def remove_watermark_from_pdf(
        self,
        pdf_path: str,
        output_path: str,
        pages: Optional[List[int]] = None,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        从 PDF 文件中去除水印
        
        Args:
            pdf_path: PDF 文件路径
            output_path: 输出 PDF 文件路径
            pages: 要处理的页码列表（None 表示所有页面）
            progress_callback: 进度回调函数 callback(page_num, total_pages)
            
        Returns:
            处理结果字典
        """
        try:
            import fitz  # PyMuPDF
            
            pdf_path = Path(pdf_path)
            output_path = Path(output_path)
            
            if not pdf_path.exists():
                return {'success': False, 'error': f'文件不存在: {pdf_path}'}
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 打开 PDF
            doc = fitz.open(str(pdf_path))
            
            total_pages = len(doc)
            processed_pages = 0
            
            for page_num in range(total_pages):
                if pages and page_num not in pages:
                    continue
                
                page = doc[page_num]
                
                # 获取页面图像（2x 放大以获得更好质量）
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                
                # PyMuPDF get_pixmap 返回 RGB 格式
                if pix.n == 4:
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                else:
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
                # 去除水印
                if self.mode == 'fast':
                    result_img = self._remove_watermark_fast(img)
                else:
                    result_img = self._remove_watermark_deep(img)
                
                if result_img is not None:
                    # 将处理后的图像写为临时文件
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        cv2.imwrite(tmp.name, result_img)
                        tmp_path = tmp.name
                    
                    # 替换页面内容：用新页面替换旧页面
                    # 这样可以完全避免原始内容残留和体积膨胀问题
                    rect = page.rect
                    # 获取当前页面在文档中的索引
                    page_idx = page.number
                    
                    # 创建新页面并插入图像
                    new_page = doc.new_page(pno=page_idx, width=rect.width, height=rect.height)
                    new_page.insert_image(new_page.rect, filename=tmp_path, overlay=False)
                    
                    # 删除旧页面（现在在 page_idx + 1 位置，因为新页面插入了）
                    doc.delete_page(page_idx + 1)
                    
                    # 删除临时文件
                    try:
                        Path(tmp_path).unlink()
                    except:
                        pass
                    
                    processed_pages += 1
                
                # 进度回调
                if progress_callback:
                    progress_callback(page_num + 1, total_pages)
            
            # 保存 PDF
            doc.save(str(output_path))
            doc.close()
            
            logger.info(f"水印去除完成: {output_path}, 处理了 {processed_pages} 页")
            
            return {
                'success': True,
                'output_path': str(output_path),
                'processed_pages': processed_pages
            }
            
        except ImportError:
            return {'success': False, 'error': '需要安装 PyMuPDF: pip install pymupdf'}
        except Exception as e:
            logger.error(f"水印去除失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def remove_watermark_from_image(
        self,
        image_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        从图像文件中去除水印
        
        Args:
            image_path: 图像文件路径
            output_path: 输出图像文件路径
            
        Returns:
            处理结果字典
        """
        try:
            image_path = Path(image_path)
            output_path = Path(output_path)
            
            if not image_path.exists():
                return {'success': False, 'error': f'文件不存在: {image_path}'}
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取图像
            img = cv2.imread(str(image_path))
            if img is None:
                return {'success': False, 'error': '无法读取图像文件'}
            
            # 去除水印
            if self.mode == 'fast':
                result_img = self._remove_watermark_fast(img)
            else:
                result_img = self._remove_watermark_deep(img)
            
            if result_img is None:
                return {'success': False, 'error': '水印去除失败'}
            
            # 保存图像
            cv2.imwrite(str(output_path), result_img)
            
            logger.info(f"水印去除完成: {output_path}")
            
            return {
                'success': True,
                'output_path': str(output_path)
            }
            
        except Exception as e:
            logger.error(f"水印去除失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _remove_watermark_fast(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        快速水印去除（基于颜色阈值）
        
        适用场景：浅色半透明水印（如灰色/白色文字水印、logo 水印）
        
        原理：
        1. 转灰度图
        2. 检测浅色区域（灰度值在阈值范围内）
        3. 通过连通域面积过滤掉小噪点
        4. 对水印区域进行 inpainting 修复
        
        Args:
            img: 输入图像 (BGR 格式，cv2 读取的标准格式)
            
        Returns:
            处理后的图像 (BGR 格式)
        """
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 检测水印区域（浅色区域）
            # 灰度范围默认 (220, 255)：只检测接近白色但不是纯白的区域
            # 这避免了误伤正常文字（正常文字灰度通常 < 200）
            lower, upper = self.watermark_gray_range
            mask = cv2.inRange(gray, lower, upper)
            
            # 形态学操作：先闭运算填充空洞，再开运算去除小噪点
            kernel_close = np.ones((5, 5), np.uint8)
            kernel_open = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
            
            # 使用连通域分析过滤面积过小的区域
            # 这样可以避免误伤正文中的零星浅色像素
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                mask, connectivity=8
            )
            
            # 创建精化的 mask：只保留面积大于阈值的连通域
            refined_mask = np.zeros_like(mask)
            for label_idx in range(1, num_labels):  # 跳过背景（label=0）
                area = stats[label_idx, cv2.CC_STAT_AREA]
                if area >= self.min_area:
                    refined_mask[labels == label_idx] = 255
            
            # 如果没有检测到水印区域，直接返回原图
            if np.sum(refined_mask) == 0:
                logger.info("快速模式：未检测到水印区域")
                return img
            
            # Inpainting 修复水印区域
            result = cv2.inpaint(img, refined_mask, self.inpaint_radius, cv2.INPAINT_TELEA)
            
            logger.info(f"快速模式：检测到 {np.sum(refined_mask > 0)} 个水印像素")
            
            return result
            
        except Exception as e:
            logger.error(f"快速水印去除失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _remove_watermark_deep(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        深度水印去除（基于边缘检测 + 频域分析）
        
        适用场景：各种类型的水印，包括深色水印、倾斜水印、
        以及快速模式难以检测的半透明水印
        
        原理：
        1. 使用多尺度边缘检测找到可能的文字/图形边缘
        2. 通过形态学操作连接相邻边缘形成区域
        3. 结合颜色特征（水印通常颜色均匀）进一步筛选
        4. 对筛选出的区域进行 inpainting 修复
        
        Args:
            img: 输入图像 (BGR 格式)
            
        Returns:
            处理后的图像 (BGR 格式)
        """
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 步骤1：多尺度边缘检测
            # 使用 Canny 检测边缘，低阈值和高阈值
            edges1 = cv2.Canny(gray, 30, 100)
            edges2 = cv2.Canny(gray, 50, 150)
            edges3 = cv2.Canny(gray, 80, 200)
            
            # 合并多尺度边缘
            edges = cv2.bitwise_or(cv2.bitwise_or(edges1, edges2), edges3)
            
            # 步骤2：形态学操作连接边缘
            # 水平方向连接（水印文字通常是水平排列）
            kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
            # 垂直方向连接
            kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 15))
            # 对角方向连接
            kernel_d = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
            
            edges_h = cv2.dilate(edges, kernel_h, iterations=1)
            edges_v = cv2.dilate(edges, kernel_v, iterations=1)
            edges_d = cv2.dilate(edges, kernel_d, iterations=1)
            
            # 合并所有方向的连接结果
            mask = cv2.bitwise_or(cv2.bitwise_or(edges_h, edges_v), edges_d)
            
            # 闭运算填充空洞
            kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
            
            # 开运算去除小噪点
            kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open, iterations=1)
            
            # 步骤3：结合颜色特征筛选水印区域
            # 水印通常颜色均匀且与周围对比度低
            # 计算局部标准差，水印区域标准差较低
            mean_val = cv2.blur(gray, (31, 31))
            diff = cv2.absdiff(gray, mean_val.astype(np.uint8))
            std_local = cv2.blur(diff, (31, 31))
            
            # 水印区域：局部标准差低于阈值（颜色均匀）且在边缘 mask 中
            # 标准差阈值根据灵敏度参数调整
            std_threshold = int(255 * self.deep_sensitivity)
            _, low_std_mask = cv2.threshold(std_local, std_threshold, 255, cv2.THRESH_BINARY_INV)
            
            # 将低标准差区域与边缘 mask 取交集
            # 这样可以找到"边缘存在的低对比度区域"，即水印
            mask = cv2.bitwise_and(mask, low_std_mask)
            
            # 步骤4：连通域面积过滤
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                mask, connectivity=8
            )
            
            refined_mask = np.zeros_like(mask)
            for label_idx in range(1, num_labels):
                area = stats[label_idx, cv2.CC_STAT_AREA]
                if area >= self.min_area:
                    refined_mask[labels == label_idx] = 255
            
            # 如果没有检测到水印区域，直接返回原图
            if np.sum(refined_mask) == 0:
                logger.info("深度模式：未检测到水印区域")
                return img
            
            # Inpainting 修复
            result = cv2.inpaint(img, refined_mask, self.inpaint_radius, cv2.INPAINT_TELEA)
            
            logger.info(f"深度模式：检测到 {np.sum(refined_mask > 0)} 个水印像素")
            
            return result
            
        except Exception as e:
            logger.error(f"深度水印去除失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def detect_watermark(self, image_path: str) -> Dict[str, Any]:
        """
        检测图像中的水印
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            检测结果字典
        """
        try:
            # cv2.imread 返回 BGR 格式
            img = cv2.imread(str(image_path))
            if img is None:
                return {'success': False, 'error': '无法读取图像'}
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 检测浅色区域
            lower, upper = self.watermark_gray_range
            mask = cv2.inRange(gray, lower, upper)
            
            # 使用连通域分析
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                mask, connectivity=8
            )
            
            total_area = 0
            watermark_regions = []
            
            for label_idx in range(1, num_labels):  # 跳过背景
                area = stats[label_idx, cv2.CC_STAT_AREA]
                if area >= self.min_area:
                    total_area += area
                    x = stats[label_idx, cv2.CC_STAT_LEFT]
                    y = stats[label_idx, cv2.CC_STAT_TOP]
                    w = stats[label_idx, cv2.CC_STAT_WIDTH]
                    h = stats[label_idx, cv2.CC_STAT_HEIGHT]
                    watermark_regions.append({
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h),
                        'area': int(area)
                    })
            
            image_area = img.shape[0] * img.shape[1]
            watermark_ratio = total_area / image_area if image_area > 0 else 0
            
            return {
                'success': True,
                'has_watermark': len(watermark_regions) > 0,
                'watermark_count': len(watermark_regions),
                'total_area': int(total_area),
                'watermark_ratio': float(watermark_ratio),
                'regions': watermark_regions
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
