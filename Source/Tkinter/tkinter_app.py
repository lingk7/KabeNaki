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

class Translator:
    """翻译器类 - 支持中文和FiXmArge魔女语"""
    def __init__(self):
        self.languages = {
            "中文": {},
            "FiXmArge": {}
        }
        self.current_language = "中文"
        self.load_translations()
    
    def load_translations(self):
        """加载翻译文本"""
        # 中文文本
        self.languages["中文"] = {
            "title": "魔法少女的魔女审判角色立绘提取工具",
            "file_processing": "文件处理",
            "select_bundle": "选择Bundle文件",
            "no_file_selected": "未选择文件",
            "processing_mode": "处理模式:",
            "auto_detect": "自动检测",
            "sprites_only": "仅提取精灵",
            "full_extraction": "完整提取",
            "ready": "就绪",
            "start_extraction": "开始提取",
            "clean_cache": "清理缓存",
            "open_output": "打开输出目录",
            "sprite_selection": "精灵选择",
            "preview": "预览",
            "auto_update_preview": "自动更新预览",
            "update_preview": "更新预览",
            "save_png": "保存PNG",
            "no_preview": "未生成预览",
            "generating": "生成中...",
            "generation_failed": "生成失败:",
            "error": "错误",
            "please_select_file": "请先选择文件",
            "processing_failed": "处理失败:",
            "complete": "完成",
            "extraction_complete": "提取完成!",
            "building_object_map": "建立对象映射...",
            "linking_components": "关联组件...",
            "building_hierarchy": "构建层级关系...",
            "extracting_sprites": "提取精灵图像...",
            "generating_data": "生成拼接数据...",
            "saving_results": "保存结果...",
            "done": "完成!",
            "extracting_sprites_progress": "提取精灵:",
            "sprites_only_mode": "仅提取精灵模式 - 无层级数据",
            "no_hierarchy_data": "无层级数据",
            "warning": "警告",
            "please_generate_first": "请先生成合成图像",
            "success": "成功",
            "image_saved": "图像已保存:",
            "cache_cleaned": "缓存清理完成!",
            "cache_clean_failed": "缓存清理失败!",
            "output_not_exist": "输出目录不存在",
            "cannot_process_sprite": "无法处理精灵",
            "load_failed": "加载失败:",
            "select_unity_bundle": "选择Unity bundle文件",
            "unity_bundle_files": "Unity Bundle files",
            "all_files": "All files",
            "save_composite": "保存合成图像",
            "png_files": "PNG files",
            "hierarchy_structure": "层级结构",
            "no_sprites_selected": "未选择精灵",
            "select_all": "全选",
            "deselect_all": "全不选",
            "reset_depth": "重置深度",
            "sprites_selected": "已选择 {} 个精灵",
            "position": "位置:",
            "original": "原始:",
            "preview_small": "预览"
        }
        
        # FiXmArge魔女语文本
        self.languages["FiXmArge"] = {
            "title": "DArime Imaje Caus-tool",
            "file_processing": "Kontora Brew",
            "select_bundle": "Seretu Kontora Scroll",
            "no_file_selected": "Nil Seretu Scroll",
            "processing_mode": "Brew Modo",
            "auto_detect": "Oto-Kenshu",
            "sprites_only": "Tada Feari ExTra",
            "full_extraction": "Kanzen ExTra",
            "ready": "Junbi Owari",
            "start_extraction": "oRei ExTra Kaishi",
            "clean_cache": "Kurai Purge",
            "open_output": "Opun Output Sanctum",
            "sprite_selection": "Feari Seretu",
            "preview": "Yogen Purebyu",
            "auto_update_preview": "Oto Yogen Koshin",
            "update_preview": "Yogen Koshin",
            "save_png": "Chozou Imaje",
            "no_preview": "Nil Yogen Hassei",
            "generating": "Yogen Hassei-chu...",
            "generation_failed": "Yogen Shippai:",
            "error": "Ayamari",
            "please_select_file": "Mazu Scroll oF Seretu",
            "processing_failed": "Brew Shippai:",
            "complete": "Kanryo",
            "extraction_complete": "ExTra Kanryo!",
            "building_object_map": "Taisho Mappu Kouchiku...",
            "linking_components": "Renkan Soshi...",
            "building_hierarchy": "Soukou Kankei Kouchiku...",
            "extracting_sprites": "Feari Imaje ExTra...",
            "generating_data": "Heitetsu Data Hassei...",
            "saving_results": "Kekka Chozou...",
            "done": "Kanryo!",
            "extracting_sprites_progress": "ExTra Feari:",
            "sprites_only_mode": "Tada Feari ExTra Modo - Nashi Soukou Data",
            "no_hierarchy_data": "Nashi Soukou Data",
            "warning": "Keikoku",
            "please_generate_first": "Mazu Gousei Imaje oF Hassei",
            "success": "Seikou",
            "image_saved": "Imaje Chozou-shi:",
            "cache_cleaned": "Kurai Purge Kanryo!",
            "cache_clean_failed": "Kurai Purge Shippai!",
            "output_not_exist": "Output Sanctum Nashi",
            "cannot_process_sprite": "Brew Deki-ni Feari",
            "load_failed": "Rodo Shippai:",
            "select_unity_bundle": "Seretu Unity Kontora Scroll",
            "unity_bundle_files": "Unity Kontora Scroll",
            "all_files": "Subete no Scroll",
            "save_composite": "Chozou Gousei Imaje",
            "png_files": "PNG Scroll",
            "hierarchy_structure": "Soukou Kozo",
            "no_sprites_selected": "Nil Seretu Feari",
            "select_all": "Zenbu Seretu",
            "deselect_all": "Zenbu Seretu-shi",
            "reset_depth": "Fukasa Risetto",
            "sprites_selected": "{} Feari Seretu-shi",
            "position": "Ichi:",
            "original": "Genshi:",
            "preview_small": "Yogen"
        }
    
    def tr(self, key, *args):
        """获取当前语言的翻译文本"""
        text = self.languages[self.current_language].get(key, key)
        if args:
            try:
                return text.format(*args)
            except:
                return text
        return text
    
    def switch_language(self, language):
        """切换语言"""
        if language in self.languages:
            self.current_language = language
            return True
        return False

class CharacterExtractor:
    """角色提取器 - 保持不变"""
    def __init__(self):
        self.temp_dir = "temp_extraction"
        self.output_dir = "extraction"
        self.ensure_directories()
        
    def ensure_directories(self):
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def clean_cache(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
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
        """完整提取角色部件 - 保持原有逻辑"""
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
            progress_callback(0, 6, "建立对象映射...")
        
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
            progress_callback(1, 6, "关联组件...")
        
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
                    "is_active": go_data["is_active"]
                }
                character_parts.append(part_data)
        
        if progress_callback:
            progress_callback(2, 6, "构建层级关系...")
        
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
            progress_callback(3, 6, "提取精灵图像...")
        
        # 第四步：提取精灵
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
                    data.image.save(output_path)
                    
                    extraction_results["sprite_mapping"][obj.path_id] = {
                        "name": sprite_name,
                        "file_path": output_path,
                        "size": [data.image.size[0], data.image.size[1]]
                    }
                    
            except Exception as e:
                continue
        
        if progress_callback:
            progress_callback(4, 6, "生成拼接数据...")
        
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
                    "category": self.categorize_part(part["name"])
                }
                extraction_results["transform_data"].append(part_data)
        
        if progress_callback:
            progress_callback(5, 6, "保存结果...")
        
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
            progress_callback(6, 6, "完成!")
        
        return extraction_results
    
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
    """精灵合成器 - 修复cheek精灵暗色问题"""
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
    
    def create_composite_image(self, sprite_data, selected_sprites=None, custom_depths=None):
        """创建合成图像 - 修复cheek精灵暗色问题"""
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
                # 确保图像以RGBA模式打开
                sprite_img = Image.open(part["sprite_path"]).convert('RGBA')
                
                # 计算位置
                pos_x = int(part["position"]["x"] * self.ratio + center_x)
                pos_y = int(part["position"]["y"] * -self.ratio + center_y)
                
                sprite_width, sprite_height = sprite_img.size
                placement_x = pos_x - sprite_width // 2
                placement_y = pos_y - sprite_height // 2
                
                # 修复cheek精灵暗色问题：使用alpha_composite而不是简单的paste
                # 这能正确处理半透明像素的混合
                if sprite_img.mode == 'RGBA' and sprite_img.getchannel('A').getbbox() is not None:
                    # 创建临时画布用于alpha合成
                    temp_canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
                    temp_canvas.paste(sprite_img, (placement_x, placement_y))
                    composite = Image.alpha_composite(composite, temp_canvas)
                else:
                    # 对于没有透明度的图像，使用普通粘贴
                    composite.paste(sprite_img, (placement_x, placement_y), sprite_img)
                
            except Exception as e:
                print(f"无法处理精灵 {part['name']}: {e}")
        
        return composite

class UnityExtractorGUI:
    """最终修复版Tkinter GUI - 解决cheek精灵暗色问题并添加多语言支持"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("魔法少女的魔女审判角色立绘提取工具")
        self.root.geometry("1400x900")
        
        # 初始化翻译器和核心组件
        self.translator = Translator()
        self.extractor = CharacterExtractor()
        self.compositor = SpriteCompositor()
        
        # 状态变量
        self.extraction_results = None
        self.selected_sprites = []
        self.custom_depths = {}
        self.composite_image = None
        self.auto_update = True  # 自动更新预览
        self.preview_update_timer = None
        
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
        
        # 标题和语言切换
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky=(tk.W, tk.E))
        
        self.title_label = ttk.Label(header_frame, text=self.translator.tr("title"), 
                                    font=("Arial", 16, "bold"))
        self.title_label.grid(row=0, column=0, sticky=tk.W)
        
        # 语言切换按钮
        self.language_button = ttk.Button(header_frame, text="FiXmArge", 
                                         command=self.switch_language)
        self.language_button.grid(row=0, column=1, sticky=tk.E)
        
        header_frame.columnconfigure(0, weight=1)
        
        # 左侧控制面板
        self.control_frame = ttk.LabelFrame(main_frame, text=self.translator.tr("file_processing"), padding="10")
        self.control_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W), padx=(0, 10))
        
        # 文件选择
        file_frame = ttk.Frame(self.control_frame)
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.select_file_button = ttk.Button(file_frame, text=self.translator.tr("select_bundle"), 
                                           command=self.select_file)
        self.select_file_button.grid(row=0, column=0, sticky=tk.W)
        
        self.file_label = ttk.Label(file_frame, text=self.translator.tr("no_file_selected"), wraplength=200)
        self.file_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # 处理模式
        mode_frame = ttk.Frame(self.control_frame)
        mode_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.mode_label = ttk.Label(mode_frame, text=self.translator.tr("processing_mode"))
        self.mode_label.grid(row=0, column=0, sticky=tk.W)
        
        self.mode_var = tk.StringVar(value=self.translator.tr("auto_detect"))
        self.mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var,
                                      values=[self.translator.tr("auto_detect"), 
                                             self.translator.tr("sprites_only"), 
                                             self.translator.tr("full_extraction")])
        self.mode_combo.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.control_frame, variable=self.progress_var)
        self.progress.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_label = ttk.Label(self.control_frame, text=self.translator.tr("ready"))
        self.progress_label.grid(row=3, column=0, sticky=tk.W)
        
        # 操作按钮
        button_frame = ttk.Frame(self.control_frame)
        button_frame.grid(row=4, column=0, sticky=(tk.W, tk.E))
        
        self.start_button = ttk.Button(button_frame, text=self.translator.tr("start_extraction"), 
                                      command=self.start_extraction)
        self.start_button.grid(row=0, column=0, sticky=tk.W)
        
        self.clean_button = ttk.Button(button_frame, text=self.translator.tr("clean_cache"), 
                                      command=self.clean_cache)
        self.clean_button.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        self.open_button = ttk.Button(button_frame, text=self.translator.tr("open_output"), 
                                     command=self.open_output_dir)
        self.open_button.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # 右侧内容区域 - 使用PanedWindow实现可调整的分割
        self.content_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.content_paned.grid(row=1, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # 左侧：精灵选择区域
        self.selection_frame = ttk.LabelFrame(self.content_paned, text=self.translator.tr("sprite_selection"), padding="10")
        self.content_paned.add(self.selection_frame, weight=1)
        
        # 右侧：预览区域
        self.preview_frame = ttk.LabelFrame(self.content_paned, text=self.translator.tr("preview"), padding="10")
        self.content_paned.add(self.preview_frame, weight=1)
        
        # 配置权重
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 初始状态
        self.show_welcome_screen()
        
        # 设置预览区域
        self.setup_preview_area()
    
    def switch_language(self):
        """切换语言"""
        current_lang = self.translator.current_language
        new_lang = "FiXmArge" if current_lang == "中文" else "中文"
        
        if self.translator.switch_language(new_lang):
            self.update_ui_language()
            # 更新语言按钮文本
            self.language_button.config(text="中文" if new_lang == "FiXmArge" else "FiXmArge")
    
    def update_ui_language(self):
        """更新UI语言"""
        # 更新标题
        self.root.title(self.translator.tr("title"))
        self.title_label.config(text=self.translator.tr("title"))
        
        # 更新控制面板
        self.control_frame.config(text=self.translator.tr("file_processing"))
        self.select_file_button.config(text=self.translator.tr("select_bundle"))
        self.file_label.config(text=self.translator.tr("no_file_selected") if not hasattr(self, 'current_file') else os.path.basename(self.current_file))
        self.mode_label.config(text=self.translator.tr("processing_mode"))
        
        # 更新模式选择框
        current_mode = self.mode_var.get()
        mode_options = [self.translator.tr("auto_detect"), 
                       self.translator.tr("sprites_only"), 
                       self.translator.tr("full_extraction")]
        self.mode_combo.config(values=mode_options)
        
        # 映射当前模式到新语言
        mode_mapping = {
            "自动检测": self.translator.tr("auto_detect"),
            "仅提取精灵": self.translator.tr("sprites_only"), 
            "完整提取": self.translator.tr("full_extraction"),
            "Oto-Kenshu": self.translator.tr("auto_detect"),
            "Tada Feari ExTra": self.translator.tr("sprites_only"),
            "Kanzen ExTra": self.translator.tr("full_extraction")
        }
        
        new_mode = mode_mapping.get(current_mode, self.translator.tr("auto_detect"))
        self.mode_var.set(new_mode)
        
        # 更新按钮文本
        self.start_button.config(text=self.translator.tr("start_extraction"))
        self.clean_button.config(text=self.translator.tr("clean_cache"))
        self.open_button.config(text=self.translator.tr("open_output"))
        
        # 更新框架标题
        self.selection_frame.config(text=self.translator.tr("sprite_selection"))
        self.preview_frame.config(text=self.translator.tr("preview"))
        
        # 更新预览区域控件
        self.auto_update_check.config(text=self.translator.tr("auto_update_preview"))
        self.update_button.config(text=self.translator.tr("update_preview"))
        self.save_button.config(text=self.translator.tr("save_png"))
        
        # 更新欢迎界面或结果界面
        if hasattr(self, 'result_notebook'):
            self.update_results_display()
        else:
            self.show_welcome_screen()
    
    def setup_preview_area(self):
        """设置预览区域"""
        # 控制按钮
        control_frame = ttk.Frame(self.preview_frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 自动更新复选框
        self.auto_update_var = tk.BooleanVar(value=True)
        self.auto_update_check = ttk.Checkbutton(control_frame, text=self.translator.tr("auto_update_preview"), 
                                                variable=self.auto_update_var,
                                                command=self.on_auto_update_changed)
        self.auto_update_check.grid(row=0, column=0, sticky=tk.W)
        
        # 手动更新按钮
        self.update_button = ttk.Button(control_frame, text=self.translator.tr("update_preview"), 
                                       command=self.generate_composite)
        self.update_button.grid(row=0, column=1, padx=(10, 0))
        
        # 保存按钮
        self.save_button = ttk.Button(control_frame, text=self.translator.tr("save_png"), 
                                     command=self.save_composite)
        self.save_button.grid(row=0, column=2, padx=(10, 0))
        
        # 状态标签
        self.preview_status = ttk.Label(control_frame, text=self.translator.tr("no_preview"))
        self.preview_status.grid(row=0, column=3, padx=(20, 0))
        
        control_frame.columnconfigure(3, weight=1)
        
        # 预览画布
        canvas_frame = ttk.Frame(self.preview_frame)
        canvas_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # 画布背景
        self.preview_canvas = tk.Canvas(canvas_frame, bg="#f0f0f0", width=600, height=600)
        self.preview_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # 添加滚动条
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.preview_canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.preview_canvas.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.preview_canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 配置权重
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.rowconfigure(1, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
    
    def show_welcome_screen(self):
        """显示欢迎界面"""
        for widget in self.selection_frame.winfo_children():
            widget.destroy()
            
        if self.translator.current_language == "中文":
            welcome_text = """
魔法少女的魔女审判角色立绘提取工具

使用说明:
1. 点击"选择Bundle文件"选择Unity bundle文件
2. 选择处理模式（自动检测/仅提取精灵/完整提取）
3. 点击"开始提取"进行处理
4. 在左侧选择要合成的部件
5. 右侧将实时显示合成预览

支持功能:
✓ 文件分类处理（Creature vs 角色）
✓ 自动精灵定位和提取
✓ 层级结构分析
✓ 深度排序合成
✓ 实时预览
            """
        else:
            welcome_text = """
DArime Imaje Caus-tool

Youhou Satsuyou:
1. "Seretu Kontora Scroll" oF tap, Unity bundle scroll oF seretu
2. Brew modo oF erabu (Oto-Kenshu / Tada Feari ExTra / Kanzen ExTra)
3. "oRei ExTra Kaishi" oF tap, brew oF okonau
4. Hidari-gawa de, gousei-suru buhin oF erabu
5. Migi-gawa de, jikkyou purebyu oF miru

Siji Kinou:
✓ Scroll Bunrui Brew (Creature vs eXi')
✓ Oto Feari Ichi-dori to ExTra
✓ Soukou Kozo Kaiseki
✓ Fukasa Junjo Gousei
✓ Jikkyou Yogen
            """
        
        text_widget = tk.Text(self.selection_frame, wrap=tk.WORD, padx=10, pady=10)
        text_widget.insert(tk.END, welcome_text)
        text_widget.config(state=tk.DISABLED)
        text_widget.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        self.selection_frame.columnconfigure(0, weight=1)
        self.selection_frame.rowconfigure(0, weight=1)
    
    def update_results_display(self):
        """更新结果显示"""
        if hasattr(self, 'result_notebook'):
            self.result_notebook.destroy()
        
        self.show_extraction_results()
    
    def on_auto_update_changed(self):
        """自动更新设置改变"""
        self.auto_update = self.auto_update_var.get()
        if self.auto_update:
            self.update_button.config(state="disabled")
            # 如果已有选择，立即更新预览
            if self.selected_sprites:
                self.schedule_preview_update()
        else:
            self.update_button.config(state="normal")
    
    def schedule_preview_update(self):
        """安排预览更新（延迟执行，避免频繁更新）"""
        if self.preview_update_timer:
            self.root.after_cancel(self.preview_update_timer)
        
        # 延迟500ms后更新，避免频繁操作导致连续生成
        self.preview_update_timer = self.root.after(500, self.generate_composite)
    
    def select_file(self):
        """选择文件"""
        file_path = filedialog.askopenfilename(
            title=self.translator.tr("select_unity_bundle"),
            filetypes=[(self.translator.tr("unity_bundle_files"), "*.bundle"), 
                      (self.translator.tr("all_files"), "*.*")]
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
            messagebox.showerror(self.translator.tr("error"), self.translator.tr("please_select_file"))
            return
        
        # 在新线程中执行提取，避免界面冻结
        def extract_thread():
            try:
                is_creature = self.extractor.is_creature_file(self.current_file)
                force_mode = self.mode_var.get()
                
                if force_mode == self.translator.tr("sprites_only"):
                    extraction_mode = "sprites_only"
                elif force_mode == self.translator.tr("full_extraction"):
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
                    self.composite_image = None
                
                self.root.after(0, self.on_extraction_complete)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(self.translator.tr("error"), 
                                                              f"{self.translator.tr('processing_failed')} {str(e)}"))
        
        threading.Thread(target=extract_thread, daemon=True).start()
    
    def on_extraction_complete(self):
        """提取完成后的处理"""
        messagebox.showinfo(self.translator.tr("complete"), self.translator.tr("extraction_complete"))
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
        self.result_notebook.add(self.sprite_tab, text=self.translator.tr("sprite_selection"))
        
        # 层级结构标签页
        self.hierarchy_tab = ttk.Frame(self.result_notebook)
        self.result_notebook.add(self.hierarchy_tab, text=self.translator.tr("hierarchy_structure"))
        
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
        
        # 添加鼠标滚轮支持
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
                
                name_label = ttk.Label(frame, text=sprite["name"], wraplength=140)
                name_label.grid(row=1, column=0, pady=(5, 0))
                
            except Exception as e:
                ttk.Label(frame, text=f"{self.translator.tr('load_failed')} {sprite['name']}").grid(row=0, column=0)
            
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
        self.update_hierarchy_tab(self.translator.tr("sprites_only_mode"))
    
    def show_character_results(self):
        """显示角色提取结果"""
        self.setup_sprite_selection()
    
    def setup_sprite_selection(self):
        """设置精灵选择界面"""
        # 清空现有内容
        for widget in self.sprite_tab.winfo_children():
            widget.destroy()
        
        if not self.extraction_results or 'transform_data' not in self.extraction_results:
            return
        
        # 创建控制按钮框架
        top_control_frame = ttk.Frame(self.sprite_tab)
        top_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.select_all_button = ttk.Button(top_control_frame, text=self.translator.tr("select_all"), 
                                          command=self.select_all)
        self.select_all_button.grid(row=0, column=0, padx=(0, 5))
        
        self.deselect_all_button = ttk.Button(top_control_frame, text=self.translator.tr("deselect_all"), 
                                            command=self.deselect_all)
        self.deselect_all_button.grid(row=0, column=1, padx=(0, 5))
        
        self.reset_depth_button = ttk.Button(top_control_frame, text=self.translator.tr("reset_depth"), 
                                           command=self.reset_depths)
        self.reset_depth_button.grid(row=0, column=2, padx=(0, 5))
        
        self.selection_count_label = ttk.Label(top_control_frame, 
                                             text=self.translator.tr("sprites_selected", len(self.selected_sprites)))
        self.selection_count_label.grid(row=0, column=3, padx=(20, 0))
        
        top_control_frame.columnconfigure(3, weight=1)
        
        # 创建分类框架
        categories = {}
        for part in self.extraction_results["transform_data"]:
            category = part["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(part)
        
        # 创建滚动框架
        canvas_frame = ttk.Frame(self.sprite_tab)
        canvas_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 添加鼠标滚轮支持
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        row = 0
        
        for category, parts in categories.items():
            # 分类框架
            category_frame = ttk.LabelFrame(scrollable_frame, text=f"{category} ({len(parts)}个部件)")
            category_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
            category_frame.columnconfigure(1, weight=1)
            
            row += 1
            
            for i, part in enumerate(parts):
                part_frame = ttk.Frame(category_frame)
                part_frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
                part_frame.columnconfigure(1, weight=1)
                
                # 选择框
                var = tk.BooleanVar(value=part["name"] in self.selected_sprites)
                check = ttk.Checkbutton(part_frame, variable=var,
                                       command=lambda p=part, v=var: self.on_sprite_toggle(p, v))
                check.grid(row=0, column=0, padx=(0, 5))
                
                # 部件信息
                info_frame = ttk.Frame(part_frame)
                info_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
                
                ttk.Label(info_frame, text=part["name"], font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W)
                ttk.Label(info_frame, text=f"{self.translator.tr('position')} ({part['position']['x']:.2f}, {part['position']['y']:.2f})",
                         font=("Arial", 8)).grid(row=1, column=0, sticky=tk.W)
                
                # 深度调整
                depth_frame = ttk.Frame(part_frame)
                depth_frame.grid(row=0, column=2, padx=(10, 0))
                
                original_depth = part["sorting_order"]
                current_depth = self.custom_depths.get(part["name"], original_depth)
                
                depth_var = tk.StringVar(value=str(current_depth))
                depth_entry = ttk.Entry(depth_frame, textvariable=depth_var, width=6,
                                       validate="key", validatecommand=(self.root.register(self.validate_number), '%P'))
                depth_entry.grid(row=0, column=0)
                depth_entry.bind('<FocusOut>', 
                               lambda e, p=part, v=depth_var: self.on_depth_change(p, v))
                
                if current_depth != original_depth:
                    ttk.Label(depth_frame, text=f"({self.translator.tr('original')} {original_depth})", 
                             font=("Arial", 7)).grid(row=1, column=0)
                
                # 预览图
                preview_frame = ttk.Frame(part_frame)
                preview_frame.grid(row=0, column=3, padx=(10, 0))
                
                try:
                    img = Image.open(part["sprite_path"])
                    img.thumbnail((50, 50), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    preview_label = ttk.Label(preview_frame, image=photo)
                    preview_label.image = photo
                    preview_label.grid(row=0, column=0)
                except:
                    ttk.Label(preview_frame, text=self.translator.tr("preview_small"), width=6).grid(row=0, column=0)
        
        canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        self.sprite_tab.columnconfigure(0, weight=1)
        self.sprite_tab.rowconfigure(1, weight=1)
    
    def select_all(self):
        """选择所有精灵"""
        if not self.extraction_results or 'transform_data' not in self.extraction_results:
            return
        
        self.selected_sprites = [part["name"] for part in self.extraction_results["transform_data"]]
        self.setup_sprite_selection()
        self.selection_count_label.config(text=self.translator.tr("sprites_selected", len(self.selected_sprites)))
        
        if self.auto_update:
            self.schedule_preview_update()
    
    def deselect_all(self):
        """取消选择所有精灵"""
        self.selected_sprites = []
        self.setup_sprite_selection()
        self.selection_count_label.config(text=self.translator.tr("sprites_selected", len(self.selected_sprites)))
        
        if self.auto_update:
            self.schedule_preview_update()
    
    def validate_number(self, value):
        """验证数字输入"""
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False
    
    def on_sprite_toggle(self, part, var):
        """精灵选择切换"""
        if var.get():
            if part["name"] not in self.selected_sprites:
                self.selected_sprites.append(part["name"])
        else:
            if part["name"] in self.selected_sprites:
                self.selected_sprites.remove(part["name"])
        
        # 更新选择计数
        self.selection_count_label.config(text=self.translator.tr("sprites_selected", len(self.selected_sprites)))
        
        # 自动更新预览
        if self.auto_update:
            self.schedule_preview_update()
    
    def on_depth_change(self, part, var):
        """深度值改变"""
        try:
            new_depth = int(var.get())
            self.custom_depths[part["name"]] = new_depth
            
            # 自动更新预览
            if self.auto_update and part["name"] in self.selected_sprites:
                self.schedule_preview_update()
        except ValueError:
            pass
    
    def reset_depths(self):
        """重置深度"""
        self.custom_depths = {}
        self.setup_sprite_selection()
        
        if self.auto_update and self.selected_sprites:
            self.schedule_preview_update()
    
    def update_hierarchy_tab(self, custom_text=None):
        """更新层级结构标签页"""
        for widget in self.hierarchy_tab.winfo_children():
            widget.destroy()
        
        text_widget = scrolledtext.ScrolledText(self.hierarchy_tab, wrap=tk.WORD, padx=10, pady=10)
        text_widget.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        if custom_text:
            text_widget.insert(tk.END, custom_text)
        elif self.extraction_results and 'hierarchy' in self.extraction_results:
            hierarchy_text = self.extractor.generate_hierarchy_text(self.extraction_results["hierarchy"])
            text_widget.insert(tk.END, hierarchy_text)
        else:
            text_widget.insert(tk.END, self.translator.tr("no_hierarchy_data"))
        
        text_widget.config(state=tk.DISABLED)
        
        self.hierarchy_tab.columnconfigure(0, weight=1)
        self.hierarchy_tab.rowconfigure(0, weight=1)
    
    def generate_composite(self):
        """生成合成图像"""
        if not self.selected_sprites:
            self.preview_status.config(text=self.translator.tr("no_sprites_selected"))
            return
        
        if not self.extraction_results or 'transform_data' not in self.extraction_results:
            return
        
        self.preview_status.config(text=self.translator.tr("generating"))
        self.root.update_idletasks()
        
        # 在新线程中生成图像，避免界面冻结
        def generate_thread():
            try:
                composite = self.compositor.create_composite_image(
                    self.extraction_results["transform_data"],
                    self.selected_sprites,
                    self.custom_depths
                )
                
                self.root.after(0, lambda: self.display_composite_image(composite))
                
            except Exception as e:
                self.root.after(0, lambda: self.preview_status.config(text=f"{self.translator.tr('generation_failed')} {str(e)}"))
        
        threading.Thread(target=generate_thread, daemon=True).start()
    
    def display_composite_image(self, composite):
        """显示合成图像"""
        if composite is None:
            self.preview_status.config(text=self.translator.tr("generation_failed"))
            return
        
        self.composite_image = composite
        self.preview_status.config(text=self.translator.tr("complete"))
        
        # 获取画布尺寸
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        if canvas_width < 10:  # 画布尚未渲染
            canvas_width = 600
            canvas_height = 600
        
        # 调整图像大小以适应画布
        img = composite.copy()
        img_width, img_height = img.size
        
        # 计算缩放比例
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        scale = min(scale_x, scale_y, 1.0)  # 不超过原始大小
        
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        if scale < 1.0:
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 为透明图像创建棋盘格背景
        if img.mode == 'RGBA':
            # 创建棋盘格背景
            checker_size = 20
            checker_img = Image.new('RGB', (new_width, new_height), color='#f0f0f0')
            draw = Image.new('RGB', (checker_size, checker_size), color='#f0f0f0')
            draw_d = ImageDraw.Draw(draw)
            draw_d.rectangle([0, 0, checker_size//2, checker_size//2], fill='#e0e0e0')
            draw_d.rectangle([checker_size//2, checker_size//2, checker_size, checker_size], fill='#e0e0e0')
            
            for y in range(0, new_height, checker_size):
                for x in range(0, new_width, checker_size):
                    checker_img.paste(draw, (x, y))
            
            # 将透明图像合成到棋盘格背景上
            checker_img.paste(img, (0, 0), img)
            display_img = checker_img
        else:
            display_img = img
        
        self.composite_photo = ImageTk.PhotoImage(display_img)
        
        # 清除画布并显示图像
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            canvas_width // 2, canvas_height // 2,
            image=self.composite_photo, anchor=tk.CENTER
        )
        
        # 更新滚动区域
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
    
    def save_composite(self):
        """保存合成图像 - 使用与预览完全相同的图像"""
        if not self.composite_image:
            messagebox.showwarning(self.translator.tr("warning"), self.translator.tr("please_generate_first"))
            return
        
        file_path = filedialog.asksaveasfilename(
            title=self.translator.tr("save_composite"),
            defaultextension=".png",
            filetypes=[(self.translator.tr("png_files"), "*.png"), (self.translator.tr("all_files"), "*.*")]
        )
        
        if file_path:
            try:
                # 直接使用预览时生成的图像，确保完全一致
                if self.composite_image.mode != 'RGBA':
                    self.composite_image = self.composite_image.convert('RGBA')
                
                self.composite_image.save(file_path, 'PNG')
                messagebox.showinfo(self.translator.tr("success"), f"{self.translator.tr('image_saved')} {file_path}")
            except Exception as e:
                messagebox.showerror(self.translator.tr("error"), f"{self.translator.tr('processing_failed')} {str(e)}")
    
    def clean_cache(self):
        """清理缓存"""
        if self.extractor.clean_cache():
            messagebox.showinfo(self.translator.tr("success"), self.translator.tr("cache_cleaned"))
        else:
            messagebox.showerror(self.translator.tr("error"), self.translator.tr("cache_clean_failed"))
    
    def open_output_dir(self):
        """打开输出目录"""
        output_dir = os.path.abspath(self.extractor.output_dir)
        if os.path.exists(output_dir):
            webbrowser.open(f"file://{output_dir}")
        else:
            messagebox.showwarning(self.translator.tr("warning"), self.translator.tr("output_not_exist"))
    
    def run(self):
        """运行应用"""
        self.root.mainloop()

def main():
    """主函数"""
    app = UnityExtractorGUI()
    app.run()

if __name__ == "__main__":
    main()