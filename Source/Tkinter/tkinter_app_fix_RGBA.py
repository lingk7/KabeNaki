import os
import sys
import json
import re
import shutil
from collections import defaultdict
import tempfile
import webbrowser
from pathlib import Path
import threading
import time

# 核心依赖
import UnityPy
import numpy as np
from PIL import Image, ImageTk, ImageDraw

# GUI依赖
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# 运行时补丁 - 修复打包问题
# archspec运行时补丁 - 修复打包问题
try:
    from archspec_patch import patch_archspec
    patch_archspec()
except ImportError:
    pass  # 开发模式下忽略

try:
    from runtime_patch import fix_archspec_issue, fix_unitypy_resources
    fix_archspec_issue()
    fix_unitypy_resources()
except ImportError:
    pass  # 开发模式下忽略

class CharacterExtractor:
    """角色提取器 - 移除混合图层功能，保留智能RGBA修正"""
    def __init__(self):
        self.output_dir = "extraction"
        self.ensure_directories()
        
    def ensure_directories(self):
        os.makedirs(self.output_dir, exist_ok=True)
    
    def clean_cache(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        self.ensure_directories()
        return True
    
    def is_creature_file(self, bundle_path):
        filename = os.path.basename(bundle_path).lower()
        creature_indicators = ['creature', 'monster', 'enemy', 'animal', 'pet']
        return any(indicator in filename for indicator in creature_indicators)
    
    def extract_sprites_only(self, bundle_path, progress_callback=None):
        env = UnityPy.load(bundle_path)
        sprites_dir = os.path.join(self.output_dir, "sprites")
        os.makedirs(sprites_dir, exist_ok=True)
        
        sprites = []
        sprite_objects = [obj for obj in env.objects if obj.type.name == "Sprite"]
        
        for i, obj in enumerate(sprite_objects):
            try:
                data = obj.read()
                sprite_name = getattr(data, "m_Name", f"Sprite_{obj.path_id}")
                
                if hasattr(data, 'image') and data.image:
                    safe_name = re.sub(r'[<>:"/\\|?*]', '_', sprite_name)
                    output_path = os.path.join(sprites_dir, f"{safe_name}.png")
                    data.image.save(output_path)
                    
                    sprites.append({
                        "name": sprite_name,
                        "file_path": output_path,
                        "path_id": obj.path_id,
                        "size": list(data.image.size)
                    })
                    
            except Exception as e:
                print(f"提取精灵失败 {obj.path_id}: {e}")
            
            if progress_callback:
                progress_callback(i + 1, len(sprite_objects), f"提取精灵: {i+1}/{len(sprite_objects)}")
        
        return sprites
    
    def extract_character_parts(self, bundle_path, progress_callback=None):
        """完整提取角色部件 - 添加智能RGBA修正"""
        env = UnityPy.load(bundle_path)
        
        extraction_results = {
            "character_parts": [],
            "hierarchy": [],
            "sprite_mapping": {},
            "transform_data": []
        }
        
        # 第一步：建立对象映射
        game_objects = {}
        transforms = {}
        sprite_renderers = {}
        
        all_objects = list(env.objects)
        
        # 步骤1: 建立对象映射
        if progress_callback:
            progress_callback(0, 7, "建立对象映射...")
        
        for obj in all_objects:
            try:
                data = obj.read()
                obj_type = obj.type.name
                
                if obj_type == "GameObject":
                    game_objects[obj.path_id] = {
                        "id": obj.path_id,
                        "name": getattr(data, "m_Name", f"GameObject_{obj.path_id}"),
                        "components": getattr(data, "m_Component", []),
                        "is_active": getattr(data, "m_IsActive", True)
                    }
                    
                elif obj_type == "Transform":
                    game_object_ref = getattr(data, "m_GameObject", None)
                    game_object_id = getattr(game_object_ref, "m_PathID", 0) if game_object_ref else 0
                    
                    transforms[obj.path_id] = {
                        "id": obj.path_id,
                        "game_object": game_object_id,
                        "local_position": self.extract_transform_position(data),
                        "local_rotation": self.extract_transform_rotation(data),
                        "local_scale": self.extract_transform_scale(data),
                        "children": getattr(data, "m_Children", []),
                        "parent": getattr(getattr(data, "m_Father", None), "m_PathID", 0) if hasattr(data, "m_Father") else 0
                    }
                    
                elif obj_type == "SpriteRenderer":
                    game_object_ref = getattr(data, "m_GameObject", None)
                    game_object_id = getattr(game_object_ref, "m_PathID", 0) if game_object_ref else 0
                    
                    sprite_ref = getattr(data, "m_Sprite", None)
                    sprite_id = getattr(sprite_ref, "m_PathID", 0) if sprite_ref else 0
                    
                    sprite_renderers[obj.path_id] = {
                        "id": obj.path_id,
                        "game_object": game_object_id,
                        "sprite": sprite_id,
                        "sorting_order": getattr(data, "m_SortingOrder", 0),
                        "color": self.extract_color(data)
                    }
                    
            except Exception as e:
                continue
        
        if progress_callback:
            progress_callback(1, 7, "关联组件...")
        
        # 第二步：关联组件
        character_parts = []
        for go_id, go_data in game_objects.items():
            transform_data = None
            for transform in transforms.values():
                if transform["game_object"] == go_id:
                    transform_data = transform
                    break
            
            sprite_renderer_data = None
            for renderer in sprite_renderers.values():
                if renderer["game_object"] == go_id:
                    sprite_renderer_data = renderer
                    break
            
            if transform_data and sprite_renderer_data:
                part_data = {
                    "name": go_data["name"],
                    "game_object_id": go_id,
                    "transform_id": transform_data["id"],
                    "sprite_renderer_id": sprite_renderer_data["id"],
                    "position": transform_data["local_position"],
                    "sorting_order": sprite_renderer_data["sorting_order"],
                    "sprite_id": sprite_renderer_data["sprite"],
                    "is_active": go_data["is_active"],
                    "initial_color": sprite_renderer_data["color"],  # 添加初始颜色
                    "color_corrected": False  # 标记是否应用了颜色修正
                }
                character_parts.append(part_data)
        
        if progress_callback:
            progress_callback(2, 7, "构建层级关系...")
        
        # 第三步：构建层级关系
        root_transforms = [t for t in transforms.values() if t["parent"] == 0]
        
        def build_hierarchy(transform_id, level=0):
            transform = transforms.get(transform_id)
            if not transform:
                return None
            
            go_id = transform["game_object"]
            game_object = game_objects.get(go_id, {})
            
            sprite_renderer = None
            for renderer in sprite_renderers.values():
                if renderer["game_object"] == go_id:
                    sprite_renderer = renderer
                    break
            
            node = {
                "name": game_object.get("name", "Unknown"),
                "game_object_id": go_id,
                "transform_id": transform_id,
                "level": level,
                "position": transform["local_position"],
                "has_sprite": sprite_renderer is not None,
                "sorting_order": sprite_renderer["sorting_order"] if sprite_renderer else 0,
                "children": []
            }
            
            for child_ref in transform["children"]:
                child_id = getattr(child_ref, "m_PathID", 0)
                if child_id:
                    child_node = build_hierarchy(child_id, level + 1)
                    if child_node:
                        node["children"].append(child_node)
            
            return node
        
        for root_transform in root_transforms:
            hierarchy = build_hierarchy(root_transform["id"])
            if hierarchy:
                extraction_results["hierarchy"].append(hierarchy)
        
        if progress_callback:
            progress_callback(3, 7, "提取精灵图像...")
        
        # 第四步：提取精灵并应用智能RGBA修正
        sprites_dir = os.path.join(self.output_dir, "sprites")
        os.makedirs(sprites_dir, exist_ok=True)
        
        sprite_objects = [obj for obj in env.objects if obj.type.name == "Sprite"]
        for i, obj in enumerate(sprite_objects):
            try:
                data = obj.read()
                sprite_name = getattr(data, "m_Name", f"Sprite_{obj.path_id}")
                
                if hasattr(data, 'image') and data.image:
                    safe_name = re.sub(r'[<>:"/\\|?*]', '_', sprite_name)
                    output_path = os.path.join(sprites_dir, f"{safe_name}.png")
                    
                    # 查找与此精灵关联的SpriteRenderer颜色
                    sprite_renderer_color = None
                    for part in character_parts:
                        if part["sprite_id"] == obj.path_id:
                            sprite_renderer_color = part["initial_color"]
                            break
                    
                    # 智能RGBA修正：只在颜色不是默认值时应用修正
                    if sprite_renderer_color and not self.is_default_color(sprite_renderer_color):
                        corrected_image = self.apply_color_correction(data.image, sprite_renderer_color)
                        corrected_image.save(output_path)
                        
                        # 标记此精灵已应用颜色修正
                        for part in character_parts:
                            if part["sprite_id"] == obj.path_id:
                                part["color_corrected"] = True
                                break
                    else:
                        # 颜色是默认值，直接保存原始图像
                        data.image.save(output_path)
                    
                    extraction_results["sprite_mapping"][obj.path_id] = {
                        "name": sprite_name,
                        "file_path": output_path,
                        "size": [data.image.size[0], data.image.size[1]]
                    }
                    
            except Exception as e:
                continue
            
            if progress_callback:
                progress_callback(i + 1, len(sprite_objects), f"提取精灵: {i+1}/{len(sprite_objects)} - {os.path.basename(output_path)}")
        
        if progress_callback:
            progress_callback(4, 7, "生成拼接数据...")
        
        # 第五步：生成拼接数据
        for part in character_parts:
            sprite_info = extraction_results["sprite_mapping"].get(part["sprite_id"])
            if sprite_info:
                part_data = {
                    "name": part["name"],
                    "sprite_name": sprite_info["name"],
                    "sprite_path": sprite_info["file_path"],
                    "sprite_size": sprite_info["size"],
                    "position": part["position"],
                    "sorting_order": part["sorting_order"],
                    "selected": False,
                    "category": self.categorize_part(part["name"]),
                    "initial_color": part["initial_color"],  # 添加初始颜色
                    "color_corrected": part["color_corrected"],  # 添加颜色修正标记
                    "custom_color": part["initial_color"].copy()  # 初始自定义颜色与初始颜色相同
                }
                extraction_results["transform_data"].append(part_data)
        
        if progress_callback:
            progress_callback(5, 7, "保存结果...")
        
        # 第六步：保存结果
        with open(os.path.join(self.output_dir, "extraction_data.json"), 'w', encoding='utf-8') as f:
            json.dump(extraction_results, f, indent=2, ensure_ascii=False)
        
        sprite_data_file = os.path.join(self.output_dir, "sprite_data.json")
        with open(sprite_data_file, 'w', encoding='utf-8') as f:
            json.dump(extraction_results["transform_data"], f, indent=2, ensure_ascii=False)
        
        hierarchy_text = self.generate_hierarchy_text(extraction_results["hierarchy"])
        with open(os.path.join(self.output_dir, "hierarchy.txt"), 'w', encoding='utf-8') as f:
            f.write(hierarchy_text)
        
        if progress_callback:
            progress_callback(6, 7, "完成!")
        
        return extraction_results
    
    def is_default_color(self, color):
        """检查颜色是否为默认值 (1.0, 1.0, 1.0, 1.0)"""
        return (abs(color["r"] - 1.0) < 0.001 and 
                abs(color["g"] - 1.0) < 0.001 and 
                abs(color["b"] - 1.0) < 0.001 and 
                abs(color["a"] - 1.0) < 0.001)
    
    def apply_color_correction(self, original_image, color_info):
        """
        应用颜色修正：模拟 Unity 的 SpriteRenderer 颜色叠加
        类似 rgbatest.py 中的实现
        """
        # 转换为 RGBA 确保有透明度通道
        if original_image.mode != 'RGBA':
            original_image = original_image.convert('RGBA')
        
        # 转换为 numpy 数组进行处理
        img_array = np.array(original_image, dtype=np.float32)
        
        # 应用颜色乘法（模拟 Unity 的渲染）
        # 注意：Unity 使用线性颜色空间，这里简化处理
        img_array[:, :, 0] *= color_info["r"]  # R 通道
        img_array[:, :, 1] *= color_info["g"]  # G 通道  
        img_array[:, :, 2] *= color_info["b"]  # B 通道
        img_array[:, :, 3] *= color_info["a"]  # A 通道
        
        # 限制数值范围并转换回 uint8
        img_array = np.clip(img_array, 0, 255)
        corrected_array = img_array.astype(np.uint8)
        
        # 创建新的 PIL 图像
        return Image.fromarray(corrected_array, 'RGBA')
    
    # 以下辅助方法保持不变
    def extract_transform_position(self, transform_data):
        try:
            pos = getattr(transform_data, "m_LocalPosition", None)
            if pos and hasattr(pos, 'x') and hasattr(pos, 'y'):
                return {
                    "x": getattr(pos, "x", 0.0),
                    "y": getattr(pos, "y", 0.0),
                    "z": getattr(pos, "z", 0.0)
                }
        except:
            pass
        return {"x": 0.0, "y": 0.0, "z": 0.0}
    
    def extract_transform_rotation(self, transform_data):
        try:
            rot = getattr(transform_data, "m_LocalRotation", None)
            if rot and hasattr(rot, 'x') and hasattr(rot, 'y'):
                return {
                    "x": getattr(rot, "x", 0.0),
                    "y": getattr(rot, "y", 0.0),
                    "z": getattr(rot, "z", 0.0),
                    "w": getattr(rot, "w", 1.0)
                }
        except:
            pass
        return {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
    
    def extract_transform_scale(self, transform_data):
        try:
            scale = getattr(transform_data, "m_LocalScale", None)
            if scale and hasattr(scale, 'x') and hasattr(scale, 'y'):
                return {
                    "x": getattr(scale, "x", 1.0),
                    "y": getattr(scale, "y", 1.0),
                    "z": getattr(scale, "z", 1.0)
                }
        except:
            pass
        return {"x": 1.0, "y": 1.0, "z": 1.0}
    
    def extract_color(self, sprite_renderer_data):
        try:
            color = getattr(sprite_renderer_data, "m_Color", None)
            if color and hasattr(color, 'r') and hasattr(color, 'g'):
                return {
                    "r": getattr(color, "r", 1.0),
                    "g": getattr(color, "g", 1.0),
                    "b": getattr(color, "b", 1.0),
                    "a": getattr(color, "a", 1.0)
                }
        except:
            pass
        return {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
    
    def categorize_part(self, part_name):
        name_lower = part_name.lower()
        
        if any(word in name_lower for word in ['body', 'torso']):
            return 'body'
        elif any(word in name_lower for word in ['head', 'face']):
            return 'head'
        elif 'arml' in name_lower or 'leftarm' in name_lower:
            return 'arm_left'
        elif 'armr' in name_lower or 'rightarm' in name_lower:
            return 'arm_right'
        elif 'arm' in name_lower:
            return 'arms'
        elif 'eye' in name_lower:
            return 'eyes'
        elif 'mouth' in name_lower:
            return 'mouth'
        elif 'hair' in name_lower:
            return 'hair'
        elif any(word in name_lower for word in ['blend', 'effect', 'shadow']):
            return 'effects'
        else:
            return 'other'
    
    def generate_hierarchy_text(self, hierarchies):
        lines = ["=== 角色层级结构 ===", ""]
        
        def add_node(node, indent=0):
            prefix = "  " * indent
            sprite_info = f" [Sprite Order: {node['sorting_order']}]" if node['has_sprite'] else ""
            pos = node['position']
            lines.append(f"{prefix}├── {node['name']} (位置: {pos['x']:.1f}, {pos['y']:.1f}){sprite_info}")
            
            for child in node['children']:
                add_node(child, indent + 1)
        
        for i, hierarchy in enumerate(hierarchies):
            lines.append(f"层级 {i+1}:")
            add_node(hierarchy)
            lines.append("")
        
        return "\n".join(lines)

class SpriteCompositor:
    """精灵合成器 - 简化版本，移除混合模式系统"""
    
    def __init__(self):
        self.ratio = 100
        self.base_canvas_size = (2000, 4000)
    
    def calculate_canvas_size(self, sprite_data, selected_sprites):
        if not sprite_data or not selected_sprites:
            return self.base_canvas_size
        
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for part in sprite_data:
            if part["name"] in selected_sprites:
                try:
                    sprite_img = Image.open(part["sprite_path"])
                    sprite_width, sprite_height = sprite_img.size
                    
                    pos_x = part["position"]["x"] * self.ratio
                    pos_y = part["position"]["y"] * -self.ratio
                    
                    left = pos_x - sprite_width // 2
                    right = pos_x + sprite_width // 2
                    top = pos_y - sprite_height // 2
                    bottom = pos_y + sprite_height // 2
                    
                    min_x = min(min_x, left)
                    max_x = max(max_x, right)
                    min_y = min(min_y, top)
                    max_y = max(max_y, bottom)
                    
                except Exception as e:
                    continue
        
        if min_x == float('inf'):
            return self.base_canvas_size
        
        width = max(2000, int(max_x - min_x) + 400)
        height = max(4000, int(max_y - min_y) + 400)
        
        return (width, height)
    
    def create_composite_image(self, sprite_data, selected_sprites=None, custom_depths=None, custom_colors=None):
        """创建合成图像 - 添加颜色调整支持"""
        if not sprite_data:
            return None
        
        if selected_sprites is None:
            selected_sprites = [part["name"] for part in sprite_data]
        
        canvas_size = self.calculate_canvas_size(sprite_data, selected_sprites)
        
        # 按深度排序
        if custom_depths and any(custom_depths.values()):
            sorted_parts = sorted(
                [part for part in sprite_data if part["name"] in selected_sprites],
                key=lambda x: custom_depths.get(x["name"], x["sorting_order"])
            )
        else:
            sorted_parts = sorted(
                [part for part in sprite_data if part["name"] in selected_sprites],
                key=lambda x: x["sorting_order"]
            )
        
        # 使用透明背景
        composite = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
        center_x = canvas_size[0] // 2
        center_y = canvas_size[1] // 2
        
        for part in sorted_parts:
            try:
                sprite_img = Image.open(part["sprite_path"]).convert('RGBA')
                
                # 应用自定义颜色调整（如果存在）
                if custom_colors and part["name"] in custom_colors:
                    custom_color = custom_colors[part["name"]]
                    # 只在颜色有变化时应用调整
                    if (abs(custom_color["r"] - 1.0) > 0.001 or 
                        abs(custom_color["g"] - 1.0) > 0.001 or
                        abs(custom_color["b"] - 1.0) > 0.001 or
                        abs(custom_color["a"] - 1.0) > 0.001):
                        sprite_img = self.apply_color_adjustment(sprite_img, custom_color)
                
                # 计算位置
                pos_x = int(part["position"]["x"] * self.ratio + center_x)
                pos_y = int(part["position"]["y"] * -self.ratio + center_y)
                
                sprite_width, sprite_height = sprite_img.size
                placement_x = pos_x - sprite_width // 2
                placement_y = pos_y - sprite_height // 2
                
                # 使用alpha_composite保持质量
                if sprite_img.mode == 'RGBA' and sprite_img.getchannel('A').getbbox() is not None:
                    temp_canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
                    temp_canvas.paste(sprite_img, (placement_x, placement_y))
                    composite = Image.alpha_composite(composite, temp_canvas)
                else:
                    composite.paste(sprite_img, (placement_x, placement_y), sprite_img)
                
            except Exception as e:
                print(f"无法处理精灵 {part['name']}: {e}")
        
        return composite
    
    def apply_color_adjustment(self, image, color_factors):
        """应用颜色调整因子到图像"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        img_array = np.array(image, dtype=np.float32)
        
        # 应用颜色乘法
        img_array[:, :, 0] *= color_factors["r"]  # R 通道
        img_array[:, :, 1] *= color_factors["g"]  # G 通道  
        img_array[:, :, 2] *= color_factors["b"]  # B 通道
        img_array[:, :, 3] *= color_factors["a"]  # A 通道
        
        # 限制数值范围并转换回 uint8
        img_array = np.clip(img_array, 0, 255)
        adjusted_array = img_array.astype(np.uint8)
        
        return Image.fromarray(adjusted_array, 'RGBA')

class UnityExtractorGUI:
    """Unity提取器GUI - 简化版本，移除混合模式功能"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎮 Unity角色提取工具")
        self.root.geometry("1400x900")
        
        # 初始化核心组件
        self.extractor = CharacterExtractor()
        self.compositor = SpriteCompositor()
        
        # 状态变量
        self.extraction_results = None
        self.selected_sprites = []
        self.custom_depths = {}
        self.custom_colors = {}  # 自定义颜色配置
        self.composite_image = None
        self.auto_update = True
        self.preview_update_timer = None
        
        self.current_file = None
        
        self.setup_gui()
    
    def setup_gui(self):
        """设置GUI界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🎮 Unity角色提取工具", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 左侧控制面板 - 固定宽度
        control_frame = ttk.LabelFrame(main_frame, text="文件处理", padding="10", width=250)
        control_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W), padx=(0, 10))
        control_frame.grid_propagate(False)  # 防止内部组件改变框架大小
        
        # 文件选择
        file_frame = ttk.Frame(control_frame)
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(file_frame, text="选择Bundle文件", 
                  command=self.select_file).grid(row=0, column=0, sticky=tk.W)
        
        self.file_label = ttk.Label(file_frame, text="未选择文件", wraplength=200)
        self.file_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # 处理模式
        mode_frame = ttk.Frame(control_frame)
        mode_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(mode_frame, text="处理模式:").grid(row=0, column=0, sticky=tk.W)
        self.mode_var = tk.StringVar(value="自动检测")
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var,
                                 values=["自动检测", "仅提取精灵", "完整提取"])
        mode_combo.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(control_frame, variable=self.progress_var)
        self.progress.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 进度标签 - 修复：移除不支持的height参数
        self.progress_label = ttk.Label(control_frame, text="就绪", wraplength=230)
        self.progress_label.grid(row=3, column=0, sticky=tk.W, pady=(5, 0))
        
        # 操作按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(button_frame, text="开始提取", 
                  command=self.start_extraction).grid(row=0, column=0, sticky=tk.W)
        
        ttk.Button(button_frame, text="清理缓存", 
                  command=self.clean_cache).grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Button(button_frame, text="打开输出目录", 
                  command=self.open_output_dir).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # 右侧内容区域
        self.content_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.content_paned.grid(row=1, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # 左侧：精灵选择区域
        self.selection_frame = ttk.LabelFrame(self.content_paned, text="精灵选择", padding="10")
        self.content_paned.add(self.selection_frame, weight=1)
        
        # 右侧：预览区域
        self.preview_frame = ttk.LabelFrame(self.content_paned, text="预览", padding="10")
        self.content_paned.add(self.preview_frame, weight=1)
        
        # 配置权重
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 初始状态
        self.show_welcome_screen()
        
        # 设置预览区域
        self.setup_preview_area()
    
    def setup_preview_area(self):
        """设置预览区域 - 简化版本，移除滚轮移动"""
        # 控制按钮
        control_frame = ttk.Frame(self.preview_frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 自动更新复选框
        self.auto_update_var = tk.BooleanVar(value=True)
        auto_update_check = ttk.Checkbutton(control_frame, text="自动更新预览", 
                                          variable=self.auto_update_var,
                                          command=self.on_auto_update_changed)
        auto_update_check.grid(row=0, column=0, sticky=tk.W)
        
        # 手动更新按钮
        self.update_button = ttk.Button(control_frame, text="更新预览", 
                                       command=self.generate_composite)
        self.update_button.grid(row=0, column=1, padx=(10, 0))
        
        # 保存按钮
        ttk.Button(control_frame, text="保存PNG", 
                  command=self.save_composite).grid(row=0, column=2, padx=(10, 0))
        
        # 状态标签
        self.preview_status = ttk.Label(control_frame, text="未生成预览")
        self.preview_status.grid(row=0, column=3, padx=(20, 0))
        
        control_frame.columnconfigure(3, weight=1)
        
        # 预览画布 - 简化版本，移除滚动条
        self.preview_canvas = tk.Canvas(self.preview_frame, bg="#f0f0f0", width=600, height=600)
        self.preview_canvas.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # 配置权重
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.rowconfigure(1, weight=1)
    
    def show_welcome_screen(self):
        """显示欢迎界面"""
        welcome_text = """
Unity角色提取工具

使用说明:
1. 点击"选择Bundle文件"选择Unity bundle文件
2. 选择处理模式（自动检测/仅提取精灵/完整提取）
3. 点击"开始提取"进行处理
4. 在左侧选择要合成的部件
5. 右侧将实时显示合成预览

主要功能:
✓ 智能RGBA修正（只修正错误的精灵）
✓ 单精灵RGBA调整（滑块控制）
✓ 文件分类处理（Creature vs 角色）
✓ 自动精灵定位和提取
✓ 层级结构分析
✓ 深度排序合成
✓ 实时预览
        """
        
        text_widget = tk.Text(self.selection_frame, wrap=tk.WORD, padx=10, pady=10)
        text_widget.insert(tk.END, welcome_text)
        text_widget.config(state=tk.DISABLED)
        text_widget.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        self.selection_frame.columnconfigure(0, weight=1)
        self.selection_frame.rowconfigure(0, weight=1)
    
    def select_file(self):
        """选择文件"""
        file_path = filedialog.askopenfilename(
            title="选择Unity bundle文件",
            filetypes=[("Unity Bundle files", "*.bundle"), ("All files", "*.*")]
        )
        
        if file_path:
            self.current_file = file_path
            self.file_label.config(text=os.path.basename(file_path))
    
    def update_progress(self, current, total, message):
        """更新进度条"""
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.progress_label.config(text=message)
        self.root.update_idletasks()
    
    def start_extraction(self):
        """开始提取"""
        if not hasattr(self, 'current_file') or not self.current_file:
            messagebox.showerror("错误", "请先选择文件")
            return
        
        # 在新线程中执行提取，避免界面冻结
        def extract_thread():
            try:
                is_creature = self.extractor.is_creature_file(self.current_file)
                force_mode = self.mode_var.get()
                
                if force_mode == "仅提取精灵":
                    extraction_mode = "sprites_only"
                elif force_mode == "完整提取":
                    extraction_mode = "full"
                else:
                    extraction_mode = "sprites_only" if is_creature else "full"
                
                def progress_callback(current, total, message):
                    self.root.after(0, lambda: self.update_progress(current, total, message))
                
                if extraction_mode == "sprites_only":
                    results = self.extractor.extract_sprites_only(self.current_file, progress_callback)
                    self.extraction_results = {"sprites": results}
                else:
                    results = self.extractor.extract_character_parts(self.current_file, progress_callback)
                    self.extraction_results = results
                    self.selected_sprites = []
                    self.custom_depths = {}
                    self.custom_colors = {}  # 重置自定义颜色
                    self.composite_image = None
                
                self.root.after(0, self.on_extraction_complete)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"处理失败: {str(e)}"))
        
        threading.Thread(target=extract_thread, daemon=True).start()
    
    def on_extraction_complete(self):
        """提取完成后的处理"""
        messagebox.showinfo("完成", "提取完成!")
        self.show_extraction_results()
    
    def show_extraction_results(self):
        """显示提取结果"""
        if not self.extraction_results:
            return
        
        # 创建结果标签页
        self.result_notebook = ttk.Notebook(self.selection_frame)
        self.result_notebook.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # 精灵选择标签页
        self.sprite_tab = ttk.Frame(self.result_notebook)
        self.result_notebook.add(self.sprite_tab, text="精灵选择")
        
        # 层级结构标签页
        self.hierarchy_tab = ttk.Frame(self.result_notebook)
        self.result_notebook.add(self.hierarchy_tab, text="层级结构")
        
        self.selection_frame.columnconfigure(0, weight=1)
        self.selection_frame.rowconfigure(0, weight=1)
        
        if 'sprites' in self.extraction_results:
            self.show_sprite_results()
        else:
            self.show_character_results()
            self.update_hierarchy_tab()
    
    def show_sprite_results(self):
        """显示精灵提取结果"""
        # 清空现有内容
        for widget in self.sprite_tab.winfo_children():
            widget.destroy()
        
        sprites = self.extraction_results['sprites']
        
        # 创建滚动框架
        canvas_frame = ttk.Frame(self.sprite_tab)
        canvas_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 添加鼠标滚轮支持到精灵显示栏
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # 显示精灵
        row, col = 0, 0
        max_cols = 4
        
        for i, sprite in enumerate(sprites):
            frame = ttk.Frame(scrollable_frame, relief="solid", padding="5")
            frame.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E))
            
            # 显示精灵预览
            try:
                img = Image.open(sprite["file_path"])
                img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                label = ttk.Label(frame, image=photo)
                label.image = photo  # 保持引用
                label.grid(row=0, column=0)
                
                # 显示精灵的原始名称
                name_label = ttk.Label(frame, text=sprite["name"], wraplength=140)
                name_label.grid(row=1, column=0, pady=(5, 0))
                
            except Exception as e:
                ttk.Label(frame, text=f"加载失败: {sprite['name']}").grid(row=0, column=0)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        self.sprite_tab.columnconfigure(0, weight=1)
        self.sprite_tab.rowconfigure(0, weight=1)
        
        # 更新层级结构标签页
        self.update_hierarchy_tab("仅提取精灵模式 - 无层级数据")
    
    def show_character_results(self):
        """显示角色提取结果"""
        self.setup_sprite_selection()
    
    def setup_sprite_selection(self):
        """设置精灵选择界面 - 添加RGBA调整功能，显示原始名称"""
        # 清空现有内容
        for widget in self.sprite_tab.winfo_children():
            widget.destroy()
        
        if not self.extraction_results or 'transform_data' not in self.extraction_results:
            # 添加错误提示
            error_label = ttk.Label(self.sprite_tab, text="没有提取数据或数据格式不正确")
            error_label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        # 创建控制按钮框架
        top_control_frame = ttk.Frame(self.sprite_tab)
        top_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(top_control_frame, text="全选", 
                  command=self.select_all).grid(row=0, column=0, padx=(0, 5))
        
        ttk.Button(top_control_frame, text="全不选", 
                  command=self.deselect_all).grid(row=0, column=1, padx=(0, 5))
        
        ttk.Button(top_control_frame, text="重置深度", 
                  command=self.reset_depths).grid(row=0, column=2, padx=(0, 5))
        
        # 新增：重置颜色按钮
        ttk.Button(top_control_frame, text="重置颜色", 
                  command=self.reset_colors).grid(row=0, column=3, padx=(0, 5))
        
        ttk.Label(top_control_frame, text=f"已选择 {len(self.selected_sprites)} 个精灵").grid(row=0, column=4, padx=(20, 0))
        
        top_control_frame.columnconfigure(4, weight=1)
        
        # 创建分类框架
        categories = {}
        transform_data = self.extraction_results["transform_data"]
        
        # 确保transform_data是列表且不为空
        if not isinstance(transform_data, list) or len(transform_data) == 0:
            error_label = ttk.Label(self.sprite_tab, text="没有找到可用的部件数据")
            error_label.grid(row=1, column=0, padx=10, pady=10)
            return
        
        for part in transform_data:
            # 确保part是字典且包含必要字段
            if not isinstance(part, dict) or "category" not in part:
                continue
                
            category = part["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(part)
        
        # 如果没有分类数据，显示提示
        if not categories:
            error_label = ttk.Label(self.sprite_tab, text="没有找到分类数据")
            error_label.grid(row=1, column=0, padx=10, pady=10)
            return
        
        # 创建滚动框架
        canvas_frame = ttk.Frame(self.sprite_tab)
        canvas_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 添加鼠标滚轮支持到精灵显示栏
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        row = 0
        
        # 遍历分类
        for category, category_parts in categories.items():
            # 分类框架
            category_frame = ttk.LabelFrame(scrollable_frame, text=f"{category} ({len(category_parts)}个部件)")
            category_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
            category_frame.columnconfigure(0, weight=1)
            
            row += 1
            
            # 遍历该分类下的所有部件
            for i, part in enumerate(category_parts):
                part_frame = ttk.Frame(category_frame)
                part_frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
                part_frame.columnconfigure(1, weight=1)
                
                # 选择框
                var = tk.BooleanVar(value=part["name"] in self.selected_sprites)
                check = ttk.Checkbutton(part_frame, variable=var,
                                       command=lambda p=part, v=var: self.on_sprite_toggle(p, v))
                check.grid(row=0, column=0, padx=(0, 5))
                
                # 部件信息 - 显示原始名称
                info_frame = ttk.Frame(part_frame)
                info_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
                
                # 显示原始名称
                name_label = ttk.Label(info_frame, text=part["name"], font=("Arial", 9, "bold"), wraplength=150)
                name_label.grid(row=0, column=0, sticky=tk.W)
                
                # 显示颜色状态
                color_status = "✓" if part.get("color_corrected", False) else "○"
                color_info = f"颜色: {color_status}"
                ttk.Label(info_frame, text=color_info, font=("Arial", 8)).grid(row=1, column=0, sticky=tk.W)
                
                ttk.Label(info_frame, text=f"位置: ({part['position']['x']:.2f}, {part['position']['y']:.2f})",
                         font=("Arial", 8)).grid(row=2, column=0, sticky=tk.W)
                
                # 深度调整
                depth_frame = ttk.Frame(part_frame)
                depth_frame.grid(row=0, column=2, padx=(10, 0))
                
                original_depth = part["sorting_order"]
                current_depth = self.custom_depths.get(part["name"], original_depth)
                
                depth_var = tk.StringVar(value=str(current_depth))
                depth_entry = ttk.Entry(depth_frame, textvariable=depth_var, width=4,
                                       validate="key", validatecommand=(self.root.register(self.validate_number), '%P'))
                depth_entry.grid(row=0, column=0)
                depth_entry.bind('<FocusOut>', 
                               lambda e, p=part, v=depth_var: self.on_depth_change(p, v))
                
                if current_depth != original_depth:
                    ttk.Label(depth_frame, text=f"(原:{original_depth})", 
                             font=("Arial", 6)).grid(row=1, column=0)
                
                # RGBA调整滑块
                color_frame = ttk.LabelFrame(part_frame, text="颜色", padding="2")
                color_frame.grid(row=0, column=3, padx=(5, 0))
                
                # 获取当前颜色值
                current_color = self.custom_colors.get(part["name"], part["initial_color"])
                
                # 创建RGBA滑块
                color_sliders = {}
                for j, channel in enumerate(["r", "g", "b", "a"]):
                    slider_frame = ttk.Frame(color_frame)
                    slider_frame.grid(row=0, column=j, padx=1)
                    
                    ttk.Label(slider_frame, text=channel.upper(), font=("Arial", 6)).grid(row=0, column=0)
                    
                    slider_var = tk.DoubleVar(value=current_color[channel])
                    slider = ttk.Scale(slider_frame, from_=0.0, to=2.0, 
                                      orient=tk.VERTICAL, variable=slider_var,
                                      length=30, command=lambda v, p=part, c=channel: self.on_color_change(p, c, float(v)))
                    slider.grid(row=1, column=0)
                    
                    value_label = ttk.Label(slider_frame, text=f"{current_color[channel]:.1f}", 
                                          font=("Arial", 6), width=3)
                    value_label.grid(row=2, column=0)
                    
                    color_sliders[channel] = {
                        "slider": slider,
                        "var": slider_var,
                        "label": value_label
                    }
                
                # 重置颜色按钮
                reset_button = ttk.Button(color_frame, text="R", 
                                        command=lambda p=part: self.reset_part_color(p),
                                        width=2)
                reset_button.grid(row=0, column=4, padx=(2, 0))
                
                # 存储滑块引用
                part["color_sliders"] = color_sliders
                
                # 预览图
                preview_frame = ttk.Frame(part_frame)
                preview_frame.grid(row=0, column=4, padx=(10, 0))
                
                try:
                    img = Image.open(part["sprite_path"])
                    img.thumbnail((40, 40), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    preview_label = ttk.Label(preview_frame, image=photo)
                    preview_label.image = photo
                    preview_label.grid(row=0, column=0)
                except Exception as e:
                    ttk.Label(preview_frame, text="预览", width=6).grid(row=0, column=0)
        
        canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.sprite_tab.columnconfigure(0, weight=1)
        self.sprite_tab.rowconfigure(1, weight=1)
    
    def on_color_change(self, part, channel, value):
        """颜色滑块改变事件"""
        # 更新自定义颜色
        if part["name"] not in self.custom_colors:
            self.custom_colors[part["name"]] = part["initial_color"].copy()
        
        self.custom_colors[part["name"]][channel] = value
        
        # 更新标签显示
        if "color_sliders" in part and channel in part["color_sliders"]:
            part["color_sliders"][channel]["label"].config(text=f"{value:.1f}")
        
        # 自动更新预览
        if self.auto_update and part["name"] in self.selected_sprites:
            self.schedule_preview_update()
    
    def reset_part_color(self, part):
        """重置单个部件的颜色"""
        if part["name"] in self.custom_colors:
            del self.custom_colors[part["name"]]
        
        # 重置滑块到初始值
        if "color_sliders" in part:
            for channel, slider_info in part["color_sliders"].items():
                initial_value = part["initial_color"][channel]
                slider_info["var"].set(initial_value)
                slider_info["label"].config(text=f"{initial_value:.1f}")
        
        # 自动更新预览
        if self.auto_update and part["name"] in self.selected_sprites:
            self.schedule_preview_update()
    
    def reset_colors(self):
        """重置所有颜色"""
        self.custom_colors = {}
        
        # 重置所有滑块
        if self.extraction_results and 'transform_data' in self.extraction_results:
            for part in self.extraction_results["transform_data"]:
                if "color_sliders" in part:
                    for channel, slider_info in part["color_sliders"].items():
                        initial_value = part["initial_color"][channel]
                        slider_info["var"].set(initial_value)
                        slider_info["label"].config(text=f"{initial_value:.1f}")
        
        # 自动更新预览
        if self.auto_update and self.selected_sprites:
            self.schedule_preview_update()
    
    def on_sprite_toggle(self, part, var):
        """精灵选择切换"""
        if var.get():
            if part["name"] not in self.selected_sprites:
                self.selected_sprites.append(part["name"])
        else:
            if part["name"] in self.selected_sprites:
                self.selected_sprites.remove(part["name"])
        
        # 更新选择计数
        self.update_selection_count()
        
        # 自动更新预览
        if self.auto_update:
            self.schedule_preview_update()
    
    def update_selection_count(self):
        """更新选择计数显示"""
        # 查找并更新选择计数标签
        for widget in self.sprite_tab.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label) and "已选择" in child.cget("text"):
                        child.config(text=f"已选择 {len(self.selected_sprites)} 个精灵")
                        return
    
    def on_depth_change(self, part, var):
        """深度值改变"""
        try:
            new_depth = int(var.get())
            self.custom_depths[part["name"]] = new_depth
            
            # 自动更新预览
            if self.auto_update and part["name"] in self.selected_sprites:
                self.schedule_preview_update()
        except ValueError:
            # 无效输入，恢复原值
            var.set(str(self.custom_depths.get(part["name"], part["sorting_order"])))
    
    def validate_number(self, value):
        """验证数字输入"""
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False
    
    def select_all(self):
        """全选所有精灵"""
        if self.extraction_results and 'transform_data' in self.extraction_results:
            self.selected_sprites = [part["name"] for part in self.extraction_results["transform_data"]]
            self.setup_sprite_selection()
            
            if self.auto_update:
                self.schedule_preview_update()
    
    def deselect_all(self):
        """全不选所有精灵"""
        self.selected_sprites = []
        self.setup_sprite_selection()
        
        if self.auto_update:
            self.schedule_preview_update()
    
    def reset_depths(self):
        """重置所有深度值"""
        self.custom_depths = {}
        self.setup_sprite_selection()
        
        if self.auto_update and self.selected_sprites:
            self.schedule_preview_update()
    
    def update_hierarchy_tab(self, message=None):
        """更新层级结构标签页"""
        # 清空现有内容
        for widget in self.hierarchy_tab.winfo_children():
            widget.destroy()
        
        if message:
            # 显示消息
            label = ttk.Label(self.hierarchy_tab, text=message)
            label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        if not self.extraction_results or 'hierarchy' not in self.extraction_results:
            label = ttk.Label(self.hierarchy_tab, text="无层级数据")
            label.grid(row=0, column=0, padx=10, pady=10)
            return
        
        # 创建文本框显示层级结构
        text_widget = scrolledtext.ScrolledText(self.hierarchy_tab, wrap=tk.WORD, width=50, height=30)
        text_widget.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # 显示层级文本
        hierarchy_text = self.extractor.generate_hierarchy_text(self.extraction_results["hierarchy"])
        text_widget.insert(tk.END, hierarchy_text)
        text_widget.config(state=tk.DISABLED)
        
        self.hierarchy_tab.columnconfigure(0, weight=1)
        self.hierarchy_tab.rowconfigure(0, weight=1)
    
    def on_auto_update_changed(self):
        """自动更新切换"""
        self.auto_update = self.auto_update_var.get()
    
    def schedule_preview_update(self):
        """安排预览更新（防抖动）"""
        if self.preview_update_timer:
            self.root.after_cancel(self.preview_update_timer)
        
        self.preview_update_timer = self.root.after(300, self.generate_composite)
    
    def generate_composite(self):
        """生成合成图像"""
        if not self.extraction_results or 'transform_data' not in self.extraction_results:
            return
        
        if not self.selected_sprites:
            self.preview_status.config(text="未选择精灵")
            return
        
        try:
            # 生成合成图像
            self.composite_image = self.compositor.create_composite_image(
                self.extraction_results["transform_data"],
                self.selected_sprites,
                self.custom_depths,
                self.custom_colors
            )
            
            if self.composite_image:
                self.display_composite_image()
                self.preview_status.config(text=f"预览已更新 ({len(self.selected_sprites)}个部件)")
            else:
                self.preview_status.config(text="生成预览失败")
                
        except Exception as e:
            self.preview_status.config(text=f"生成预览错误: {str(e)}")
    
    def display_composite_image(self):
        """显示合成图像 - 修复拖影问题"""
        if not self.composite_image:
            return
        
        # 清除画布内容
        self.preview_canvas.delete("all")
        
        # 调整图像大小以适应画布
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width, canvas_height = 600, 600
        
        img = self.composite_image.copy()
        img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        
        # 转换为PhotoImage
        self.preview_photo = ImageTk.PhotoImage(img)
        
        # 显示图像
        self.preview_canvas.create_image(
            canvas_width // 2, canvas_height // 2,
            image=self.preview_photo, anchor=tk.CENTER
        )
    
    def save_composite(self):
        """保存合成图像"""
        if not self.composite_image:
            messagebox.showwarning("警告", "没有可保存的合成图像")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="保存合成图像",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.composite_image.save(file_path)
                messagebox.showinfo("成功", f"图像已保存到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def clean_cache(self):
        """清理缓存"""
        if self.extractor.clean_cache():
            messagebox.showinfo("成功", "缓存已清理")
        else:
            messagebox.showerror("错误", "清理缓存失败")
    
    def open_output_dir(self):
        """打开输出目录"""
        output_dir = os.path.abspath(self.extractor.output_dir)
        if os.path.exists(output_dir):
            webbrowser.open(f"file://{output_dir}")
        else:
            messagebox.showwarning("警告", "输出目录不存在")
    
    def run(self):
        """运行应用"""
        self.root.mainloop()

def main():
    """主函数"""
    app = UnityExtractorGUI()
    app.run()

if __name__ == "__main__":
    main()