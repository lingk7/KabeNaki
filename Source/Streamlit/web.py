import streamlit as st
import UnityPy
import json
import os
import re
import shutil
from collections import defaultdict
from PIL import Image, ImageDraw
import numpy as np
import tempfile
import webbrowser
import time
from pathlib import Path

# 设置页面
st.set_page_config(
    page_title="Unity角色提取工具",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

class CharacterExtractor:
    def __init__(self):
        self.temp_dir = "temp_extraction"
        self.output_dir = "extraction"
        self.ensure_directories()
        
    def ensure_directories(self):
        """确保必要的目录存在"""
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def clean_cache(self):
        """清理提取缓存"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        self.ensure_directories()
        return True
    
    def is_creature_file(self, bundle_path):
        """判断是否为creature文件（根据文件名或内容）"""
        filename = os.path.basename(bundle_path).lower()
        creature_indicators = ['creature', 'monster', 'enemy', 'animal', 'pet']
        return any(indicator in filename for indicator in creature_indicators)
    
    def extract_sprites_only(self, bundle_path, progress_bar):
        """仅提取精灵（用于creature文件）"""
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
                st.warning(f"提取精灵失败 {obj.path_id}: {e}")
            
            progress_bar.progress((i + 1) / len(sprite_objects), text=f"提取精灵: {i+1}/{len(sprite_objects)}")
        
        return sprites
    
    def extract_character_parts(self, bundle_path, progress_bar):
        """完整提取角色部件（用于非creature文件）"""
        env = UnityPy.load(bundle_path)
        
        # 存储提取结果
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
        
        # 进度子步骤
        progress_steps = 6
        current_step = 0
        
        # 步骤1: 建立对象映射
        progress_bar.progress(current_step / progress_steps, text="建立对象映射...")
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
        
        current_step += 1
        progress_bar.progress(current_step / progress_steps, text="关联组件...")
        
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
        
        current_step += 1
        progress_bar.progress(current_step / progress_steps, text="构建层级关系...")
        
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
        
        current_step += 1
        progress_bar.progress(current_step / progress_steps, text="提取精灵图像...")
        
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
        
        current_step += 1
        progress_bar.progress(current_step / progress_steps, text="生成拼接数据...")
        
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
                    "selected": False,  # 默认不选中
                    "category": self.categorize_part(part["name"])
                }
                extraction_results["transform_data"].append(part_data)
        
        current_step += 1
        progress_bar.progress(current_step / progress_steps, text="保存结果...")
        
        # 第六步：保存结果
        with open(os.path.join(self.output_dir, "extraction_data.json"), 'w', encoding='utf-8') as f:
            json.dump(extraction_results, f, indent=2, ensure_ascii=False)
        
        sprite_data_file = os.path.join(self.output_dir, "sprite_data.json")
        with open(sprite_data_file, 'w', encoding='utf-8') as f:
            json.dump(extraction_results["transform_data"], f, indent=2, ensure_ascii=False)
        
        hierarchy_text = self.generate_hierarchy_text(extraction_results["hierarchy"])
        with open(os.path.join(self.output_dir, "hierarchy.txt"), 'w', encoding='utf-8') as f:
            f.write(hierarchy_text)
        
        return extraction_results
    
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
    def __init__(self):
        self.ratio = 100  # 与原脚本相同的比例因子
        self.base_canvas_size = (2000, 4000)  # 与原脚本相同的画布大小
    
    def calculate_canvas_size(self, sprite_data, selected_sprites):
        """动态计算所需的画布大小 - 参考原脚本逻辑"""
        if not sprite_data or not selected_sprites:
            return self.base_canvas_size
        
        # 找出所有选中精灵的边界
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for part in sprite_data:
            if part["name"] in selected_sprites:
                try:
                    sprite_img = Image.open(part["sprite_path"])
                    sprite_width, sprite_height = sprite_img.size
                    
                    # 使用原脚本的坐标计算逻辑
                    pos_x = part["position"]["x"] * self.ratio
                    pos_y = part["position"]["y"] * -self.ratio  # Y轴翻转
                    
                    # 计算精灵的边界
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
        
        # 计算所需的画布大小
        if min_x == float('inf'):  # 没有有效的精灵
            return self.base_canvas_size
        
        width = max(2000, int(max_x - min_x) + 400)  # 添加边距
        height = max(4000, int(max_y - min_y) + 400)
        
        return (width, height)
    
    def create_composite_image(self, sprite_data, selected_sprites=None, custom_depths=None):
        """创建合成图像 - 修复预览与合成不一致的问题"""
        if not sprite_data:
            return None
        
        if selected_sprites is None:
            selected_sprites = [part["name"] for part in sprite_data]
        
        # 动态计算画布大小
        canvas_size = self.calculate_canvas_size(sprite_data, selected_sprites)
        
        # 使用自定义深度或原始深度进行排序
        if custom_depths and any(custom_depths.values()):
            # 使用自定义深度
            sorted_parts = sorted(
                [part for part in sprite_data if part["name"] in selected_sprites],
                key=lambda x: custom_depths.get(x["name"], x["sorting_order"])
            )
        else:
            # 使用原始深度
            sorted_parts = sorted(
                [part for part in sprite_data if part["name"] in selected_sprites],
                key=lambda x: x["sorting_order"]
            )
        
        # 创建画布 - 使用白色背景而不是透明背景，避免暗色问题
        composite = Image.new('RGBA', canvas_size, (255, 255, 255, 255))
        
        # 计算中心偏移
        center_x = canvas_size[0] // 2
        center_y = canvas_size[1] // 2
        
        for part in sorted_parts:
            try:
                sprite_img = Image.open(part["sprite_path"]).convert('RGBA')
                
                # 使用原脚本的坐标计算逻辑
                pos_x = int(part["position"]["x"] * self.ratio + center_x)
                pos_y = int(part["position"]["y"] * -self.ratio + center_y)  # Y轴翻转
                
                # 计算放置位置 - 精灵中心对准计算得到的位置
                sprite_width, sprite_height = sprite_img.size
                placement_x = pos_x - sprite_width // 2
                placement_y = pos_y - sprite_height // 2
                
                # 将精灵绘制到合成图像上 - 使用简单的粘贴方法，避免复杂的alpha混合
                composite.paste(sprite_img, (placement_x, placement_y), sprite_img)
                
            except Exception as e:
                st.warning(f"无法处理精灵 {part['name']}: {e}")
        
        return composite
    
    def get_sprite_preview(self, sprite_path, size=(200, 200)):
        """获取精灵预览 - 增大预览尺寸解决模糊问题"""
        try:
            img = Image.open(sprite_path)
            
            # 保持宽高比的同时缩放到指定大小
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 如果图像尺寸小于预览尺寸，创建适当大小的画布
            if img.size[0] < size[0] or img.size[1] < size[1]:
                # 创建透明背景
                background = Image.new('RGBA', size, (0, 0, 0, 0))
                # 计算居中位置
                x = (size[0] - img.size[0]) // 2
                y = (size[1] - img.size[1]) // 2
                # 将图像粘贴到背景上
                background.paste(img, (x, y), img)
                return background
            else:
                return img
        except Exception as e:
            st.error(f"加载预览失败: {e}")
            return None

def main():
    st.title("🎮 Unity角色提取工具")
    st.markdown("上传Unity bundle文件，自动提取角色部件并进行合成")
    
    # 初始化类
    extractor = CharacterExtractor()
    compositor = SpriteCompositor()
    
    # 初始化session state
    if 'extraction_complete' not in st.session_state:
        st.session_state.extraction_complete = False
    if 'extraction_results' not in st.session_state:
        st.session_state.extraction_results = None
    if 'selected_sprites' not in st.session_state:
        st.session_state.selected_sprites = []
    if 'auto_update_composite' not in st.session_state:
        st.session_state.auto_update_composite = True
    if 'composite_image' not in st.session_state:
        st.session_state.composite_image = None
    if 'custom_depths' not in st.session_state:
        st.session_state.custom_depths = {}
    
    # 侧边栏 - 文件上传和设置
    with st.sidebar:
        st.header("文件处理")
        
        # 文件上传
        uploaded_file = st.file_uploader("选择Unity bundle文件", type=['bundle'])
        
        if uploaded_file is not None:
            # 保存上传的文件
            temp_path = os.path.join(extractor.temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"已上传: {uploaded_file.name}")
            
            # 确定处理模式
            is_creature = extractor.is_creature_file(temp_path)
            force_mode = st.selectbox("处理模式", ["自动检测", "仅提取精灵", "完整提取"])
            
            if force_mode == "仅提取精灵":
                extraction_mode = "sprites_only"
            elif force_mode == "完整提取":
                extraction_mode = "full"
            else:
                extraction_mode = "sprites_only" if is_creature else "full"
            
            st.info(f"检测模式: {'Creature文件 - 仅提取精灵' if extraction_mode == 'sprites_only' else '角色文件 - 完整提取'}")
            
            # 处理按钮
            if st.button("开始提取", type="primary"):
                progress_bar = st.progress(0, text="开始处理...")
                
                try:
                    if extraction_mode == "sprites_only":
                        # 仅提取精灵
                        sprites = extractor.extract_sprites_only(temp_path, progress_bar)
                        st.session_state.extraction_results = {"sprites": sprites}
                        st.session_state.extraction_complete = True
                        
                    else:
                        # 完整提取
                        results = extractor.extract_character_parts(temp_path, progress_bar)
                        st.session_state.extraction_results = results
                        st.session_state.extraction_complete = True
                        st.session_state.selected_sprites = []  # 重置选择
                        st.session_state.composite_image = None  # 重置合成图像
                        st.session_state.custom_depths = {}  # 重置自定义深度
                    
                    st.success("提取完成!")
                    
                except Exception as e:
                    st.error(f"处理失败: {str(e)}")
                    st.exception(e)
        
        st.header("设置")
        
        # 缓存清理
        if st.button("🧹 清理缓存"):
            if extractor.clean_cache():
                st.success("缓存清理完成!")
            else:
                st.error("缓存清理失败!")
        
        # 手动打开目录按钮
        if st.button("📁 打开输出目录"):
            output_dir = os.path.abspath(extractor.output_dir)
            if os.path.exists(output_dir):
                webbrowser.open(f"file://{output_dir}")
                st.success(f"已打开目录: {output_dir}")
            else:
                st.error("输出目录不存在")
        
        # 如果是完整提取模式，显示精灵选择
        if st.session_state.extraction_complete and st.session_state.extraction_results and 'transform_data' in st.session_state.extraction_results:
            st.header("精灵选择")
            
            # 实时更新开关
            st.session_state.auto_update_composite = st.checkbox("实时更新合成图像", value=True)
            
            # 重置选项按钮 - 替换全选/全不选
            if st.button("🔄 重置所有选项"):
                st.session_state.selected_sprites = []
                st.session_state.custom_depths = {}
                st.session_state.composite_image = None
                st.success("已重置所有选项")
            
            # 分类显示
            categories = {}
            for part in st.session_state.extraction_results["transform_data"]:
                category = part["category"]
                if category not in categories:
                    categories[category] = []
                categories[category].append(part)
            
            # 选择要合成的精灵
            for category, parts in categories.items():
                # 默认展开所有分类
                with st.expander(f"{category} ({len(parts)}个部件)", expanded=True):
                    for part in parts:
                        col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
                        with col1:
                            # 使用非空标签，并隐藏标签
                            checkbox_label = f"选择 {part['name']}"
                            is_checked = st.checkbox(
                                checkbox_label, 
                                value=part["name"] in st.session_state.selected_sprites,
                                key=f"checkbox_{part['name']}",
                                label_visibility="collapsed"
                            )
                            # 直接更新选择状态，不需要条件判断
                            if is_checked and part["name"] not in st.session_state.selected_sprites:
                                st.session_state.selected_sprites.append(part["name"])
                            elif not is_checked and part["name"] in st.session_state.selected_sprites:
                                st.session_state.selected_sprites.remove(part["name"])
                        with col2:
                            st.write(f"**{part['name']}**")
                            st.write(f"位置: ({part['position']['x']:.2f}, {part['position']['y']:.2f})")
                        with col3:
                            # 深度调整 - 修复最大值限制问题
                            original_depth = part["sorting_order"]
                            current_depth = st.session_state.custom_depths.get(part["name"], original_depth)
                            
                            # 动态计算最大最小值，确保能容纳原始深度
                            min_depth = min(-100, original_depth - 50)
                            max_depth = max(200, original_depth + 50)  # 增加最大值范围
                            
                            new_depth = st.number_input(
                                f"深度",
                                min_value=min_depth,
                                max_value=max_depth,
                                value=current_depth,
                                key=f"depth_{part['name']}",
                                step=1,
                                help=f"原始深度: {original_depth}"
                            )
                            
                            if new_depth != current_depth:
                                st.session_state.custom_depths[part["name"]] = new_depth
                                # 如果启用了实时更新，更新合成图像
                                if st.session_state.auto_update_composite and part["name"] in st.session_state.selected_sprites:
                                    composite = compositor.create_composite_image(
                                        st.session_state.extraction_results["transform_data"], 
                                        st.session_state.selected_sprites,
                                        st.session_state.custom_depths
                                    )
                                    st.session_state.composite_image = composite
                            
                            # 显示深度状态
                            if new_depth != original_depth:
                                st.caption(f"自定义: {new_depth} (原始: {original_depth})")
                            else:
                                st.caption(f"原始深度: {original_depth}")
                        with col4:
                            # 使用更大的预览图
                            preview = compositor.get_sprite_preview(part["sprite_path"], (80, 80))
                            if preview:
                                st.image(preview, use_container_width=True)
            
            st.write(f"已选择 {len(st.session_state.selected_sprites)} 个精灵")
            
            # 重置深度按钮
            if st.button("🔄 重置所有深度"):
                st.session_state.custom_depths = {}
                if st.session_state.auto_update_composite and st.session_state.selected_sprites:
                    composite = compositor.create_composite_image(
                        st.session_state.extraction_results["transform_data"], 
                        st.session_state.selected_sprites,
                        st.session_state.custom_depths
                    )
                    st.session_state.composite_image = composite
                st.success("已重置所有深度设置")
            
            # 当选择发生变化时更新合成图像
            if st.session_state.auto_update_composite and st.session_state.selected_sprites:
                composite = compositor.create_composite_image(
                    st.session_state.extraction_results["transform_data"], 
                    st.session_state.selected_sprites,
                    st.session_state.custom_depths
                )
                st.session_state.composite_image = composite
    
    # 主内容区域
    if not st.session_state.extraction_complete:
        # 显示使用说明
        st.markdown("""
        ## 使用说明
        
        1. **上传文件**: 在左侧边栏选择Unity bundle文件进行上传
        2. **自动分类**: 
           - Creature文件: 仅提取精灵图像
           - 角色文件: 完整提取，包括层级关系和位置数据
        3. **合成功能**: 对于角色文件，可以在画布上自动定位并合成精灵
        
        ## 支持的功能
        
        - ✅ 文件分类处理（Creature vs 角色）
        - ✅ 提取缓存管理
        - ✅ 自动精灵定位
        - ✅ 深度排序合成
        - ✅ 实时预览
        - ✅ 分类浏览
        - ✅ 手动打开目录
        - ✅ 深度调整功能
        - ✅ 进度条显示
        """)
    
    else:
        # 显示提取结果
        if st.session_state.extraction_results:
            if 'sprites' in st.session_state.extraction_results:
                # 精灵提取模式
                st.success(f"精灵提取完成! 共提取 {len(st.session_state.extraction_results['sprites'])} 个精灵")
                
                # 显示精灵预览 - 使用更大的预览图和更少的列数解决模糊问题
                st.subheader("提取的精灵")
                
                # 根据精灵数量决定列数
                sprites_count = len(st.session_state.extraction_results['sprites'])
                if sprites_count <= 4:
                    cols = st.columns(2)  # 精灵较少时使用2列
                else:
                    cols = st.columns(3)  # 精灵较多时使用3列
                
                for i, sprite in enumerate(st.session_state.extraction_results['sprites']):
                    with cols[i % len(cols)]:
                        # 使用更大的预览图解决模糊问题
                        preview = compositor.get_sprite_preview(sprite["file_path"], (300, 300))
                        if preview:
                            st.image(preview, caption=sprite["name"], use_container_width=True)
                        else:
                            st.write(f"❌ {sprite['name']}")
            
            else:
                # 完整提取模式
                results = st.session_state.extraction_results
                st.success(f"提取完成! 共提取 {len(results['transform_data'])} 个角色部件")
                
                # 显示层级结构
                with st.expander("层级结构"):
                    hierarchy_text = extractor.generate_hierarchy_text(results["hierarchy"])
                    st.text(hierarchy_text)
                
                # 精灵合成界面
                st.subheader("精灵合成")
                
                # 显示合成图像
                if st.session_state.composite_image:
                    st.image(st.session_state.composite_image, caption="合成图像", use_container_width=True)
                    
                    # 保存选项
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 保存PNG"):
                            save_path = os.path.join(extractor.output_dir, "composite.png")
                            st.session_state.composite_image.save(save_path)
                            st.success(f"图像已保存: {save_path}")
                    
                    with col2:
                        if st.button("📋 复制到剪贴板"):
                            st.info("复制功能需要额外的浏览器权限")
                else:
                    if st.session_state.selected_sprites:
                        st.info("正在生成合成图像...")
                    else:
                        st.info("请在左侧边栏选择要合成的精灵")
                
                # 手动生成按钮（当实时更新关闭时）
                if not st.session_state.auto_update_composite and st.session_state.selected_sprites:
                    if st.button("生成合成图像"):
                        composite = compositor.create_composite_image(
                            results["transform_data"], 
                            st.session_state.selected_sprites,
                            st.session_state.custom_depths
                        )
                        st.session_state.composite_image = composite
                        st.rerun()

if __name__ == "__main__":
    main()