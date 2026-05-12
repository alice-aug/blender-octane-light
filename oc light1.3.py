bl_info = {
    "name": "OC灯光控制面板",
    "author": "Alice&DE",
    "version": (1, 3),
    "blender": (4, 2),
    "location": "3D视图 > N 面板 > OC灯光",
    "description": "增加了自定义快捷键",
    "category": "照明",
    "doc_url": "https://www.bilibili.com/video/BV1CuhFzNExw/?spm_id_from=333.1387.homepage.video_card.click&vd_source=ad10015b0dbdd90540ba4621fa36cf02"
}

import bpy

class OCAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    # 弹窗快捷键配置
    popup_key: bpy.props.StringProperty(
        name="弹窗快捷键",
        description="设置弹窗快捷键（如 Ctrl+D）",
        default="D",
    )
    popup_ctrl: bpy.props.BoolProperty(name="Ctrl", default=True)
    popup_shift: bpy.props.BoolProperty(name="Shift", default=False)
    popup_alt: bpy.props.BoolProperty(name="Alt", default=False)

    # 灯光独显快捷键配置
    solo_key: bpy.props.StringProperty(
        name="灯光独显快捷键",
        description="设置灯光独显快捷键（如 Ctrl+Shift+S）",
        default="S",
    )
    solo_ctrl: bpy.props.BoolProperty(name="Ctrl", default=True)
    solo_shift: bpy.props.BoolProperty(name="Shift", default=False)
    solo_alt: bpy.props.BoolProperty(name="Alt", default=False)

    def draw(self, context):
        layout = self.layout
        layout.label(text="设置快捷键")

        # 弹窗快捷键设置
        layout.label(text="弹窗快捷键设置")
        layout.prop(self, "popup_key", text="快捷键")
        row = layout.row(align=True)
        row.prop(self, "popup_ctrl")
        row.prop(self, "popup_shift")
        row.prop(self, "popup_alt")

        layout.separator()

        # 灯光独显快捷键设置
        layout.label(text="灯光独显快捷键设置")
        layout.prop(self, "solo_key", text="快捷键")
        row = layout.row(align=True)
        row.prop(self, "solo_ctrl")
        row.prop(self, "solo_shift")
        row.prop(self, "solo_alt")

# —— 批量灯光ID：Alt+滑块时使用 timer 防抖同步（抵消 Blender delta 行为） —— #
_sync_id_val = None
_sync_id_timer = None
_update_locked = False

def _do_sync_light_id():
    global _sync_id_val, _sync_id_timer, _update_locked
    if _sync_id_val is not None:
        _update_locked = True
        ctx = bpy.context
        for obj in ctx.selected_objects:
            if obj.type == 'LIGHT':
                obj.data.octane_diffuse_feedback_7 = _sync_id_val
        _update_locked = False
    _sync_id_val = None
    _sync_id_timer = None

# —— 更新 Texture Emission 节点输入 & 重命名灯光 —— #
def update_diffuse_feedback(light_data, context):
    global _update_locked, _sync_id_val, _sync_id_timer

    if _update_locked:
        return

    # 通过 light_data 找到引用它的物体（支持批量设置时非活跃对象也能正确更新）
    nt = getattr(light_data, "node_tree", None)
    if nt:
        node = nt.nodes.get("Texture emission")
        if node:
            try:
                node.inputs[7].default_value  = light_data.octane_diffuse_feedback_7
                node.inputs[9].default_value  = light_data.octane_diffuse_feedback
                node.inputs[10].default_value = light_data.octane_diffuse_feedback_10
                node.inputs[11].default_value = light_data.octane_diffuse_feedback_11
                node.inputs[12].default_value = light_data.octane_diffuse_feedback_12
                node.inputs[13].default_value = light_data.octane_diffuse_feedback_13
            except Exception as e:
                print(f"[OC灯光面板] 节点输入更新失败: {e}")
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT' and obj.data == light_data:
            try:
                id_val = light_data.octane_diffuse_feedback_7
                obj.name = f"{id_val}_light"
            except Exception as e:
                print(f"[OC灯光面板] 重命名失败: {e}")
            break

    # Alt+滑块防抖：活跃灯光 ID 变更且存在其他选中灯光时，延迟强制同步绝对值
    active = context.object
    if active and active.type == 'LIGHT' and active.data == light_data:
        others = [o for o in context.selected_objects if o.type == 'LIGHT' and o.data != light_data]
        if others:
            _sync_id_val = light_data.octane_diffuse_feedback_7
            if _sync_id_timer is not None:
                try:
                    bpy.app.timers.unregister(_sync_id_timer)
                except Exception:
                    pass
            _sync_id_timer = bpy.app.timers.register(_do_sync_light_id, first_interval=0.12)

# —— Octane Diffuse Feedback Properties —— #
bpy.types.Light.octane_diffuse_feedback_7 = bpy.props.IntProperty(
    name="灯光 ID", description="控制 Texture emission 的 Input[7]",
    default=1, min=1, max=20, update=update_diffuse_feedback
)
bpy.types.Light.octane_diffuse_feedback = bpy.props.BoolProperty(
    name="漫射", description="控制 Input[9]",
    default=True, update=update_diffuse_feedback
)
bpy.types.Light.octane_diffuse_feedback_10 = bpy.props.BoolProperty(
    name="反射", description="控制 Input[10]",
    default=True, update=update_diffuse_feedback
)
bpy.types.Light.octane_diffuse_feedback_11 = bpy.props.BoolProperty(
    name="散射", description="控制 Input[11]",
    default=True, update=update_diffuse_feedback
)
bpy.types.Light.octane_diffuse_feedback_12 = bpy.props.BoolProperty(
    name="透明自发光", description="控制 Input[12]",
    default=True, update=update_diffuse_feedback
)
bpy.types.Light.octane_diffuse_feedback_13 = bpy.props.BoolProperty(
    name="投射阴影", description="控制 Input[13]",
    default=True, update=update_diffuse_feedback
)

# —— 切换 Octane Light ID 布尔属性并刷新 —— #
def toggle_octane_bool(self, context, prop_name):
    obj = context.object
    if obj and hasattr(obj, "octane"):
        octane = obj.octane
        if hasattr(octane, prop_name):
            val = getattr(octane, prop_name)
            setattr(octane, prop_name, not val)
            # 微移刷新
            loc = obj.location.copy()
            obj.location.x += 0.0001
            obj.location = loc
            for area in context.screen.areas:
                if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                    area.tag_redraw()

# —— 动态创建 Octane Light ID toggle 操作符 —— #
def make_octane_toggle(prop_name, label):
    op_id = f"light.toggle_{prop_name}"
    cls_name = f"LIGHT_OT_toggle_{prop_name}"
    def exec_fn(self, context):
        if getattr(self, "_alt_batch", False):
            objs = [o for o in context.selected_objects if hasattr(o, "octane") and hasattr(o.octane, prop_name)]
            if objs:
                all_on = all(getattr(o.octane, prop_name) for o in objs)
                target = not all_on
                for o in objs:
                    setattr(o.octane, prop_name, target)
                    o.update_tag()
                context.view_layer.update()
        else:
            toggle_octane_bool(self, context, prop_name)
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                area.tag_redraw()
        return {'FINISHED'}

    def inv_fn(self, context, event):
        self._alt_batch = event.alt and len(context.selected_objects) > 1
        return self.execute(context)

    return type(cls_name, (bpy.types.Operator,), {
        "bl_idname": op_id,
        "bl_label": label,
        "execute": exec_fn,
        "invoke": inv_fn,
    })

# —— 主 UI 面板 —— #
class OC_PT_light_panel(bpy.types.Panel):
    bl_label = "OC灯光控制"
    bl_idname = "OC_PT_light_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OC灯光"

    @classmethod
    def poll(cls, context):
        if context.object and context.object.type in {'LIGHT', 'MESH'}:
            return True
        if context.selected_objects:
            return any(o.type in {'LIGHT', 'MESH'} for o in context.selected_objects)
        return False

    def draw(self, context):
        layout = self.layout
        obj = context.object
        selected = context.selected_objects

        if obj and obj.type == 'LIGHT':
            light = obj.data
            layout.label(text="灯光 ID & 可见性")
            layout.prop(light, "octane_diffuse_feedback_7", slider=True)

            row = layout.row(align=True)
            for prop, lbl in [
                ("octane_diffuse_feedback",   "漫射"),
                ("octane_diffuse_feedback_10","反射"),
                ("octane_diffuse_feedback_11","散射"),
                ("octane_diffuse_feedback_12","透明"),
                ("octane_diffuse_feedback_13","阴影")
            ]:
                val = getattr(light, prop)
                btn = row.operator("light.toggle_feedback", text=lbl, depress=val)
                btn.feedback_type = prop

            layout.separator()
            layout.operator("light.toggle_solo_light", text="灯光独显", icon='RESTRICT_VIEW_OFF')
            layout.separator()

        if obj and hasattr(obj, "octane"):
            multi = len(selected) > 1
            mask_objs = [o for o in selected if hasattr(o, "octane")] if multi else []
            multi = multi and len(mask_objs) > 1

            if multi:
                layout.label(text="灯光通道遮罩（选中物体集体状态）")
            else:
                layout.label(text="灯光通道遮罩")
            scale = 0.7

            def _depress(objs, pname):
                if multi:
                    return all(hasattr(o.octane, pname) and getattr(o.octane, pname) for o in objs)
                return getattr(obj.octane, pname)

            row = layout.row(align=True)
            row.scale_x = scale
            row.operator("light.toggle_light_id_sunlight", text="S", depress=_depress(mask_objs, "light_id_sunlight"))
            row.operator("light.toggle_light_id_env",       text="E", depress=_depress(mask_objs, "light_id_env"))

            row = layout.row(align=True)
            row.scale_x = scale
            for i in range(1, 11):
                pname = f"light_id_pass_{i}"
                if hasattr(obj.octane, pname):
                    row.operator(f"light.toggle_{pname}", text=str(i), depress=_depress(mask_objs, pname))

            row = layout.row(align=True)
            row.scale_x = scale
            for i in range(11, 21):
                pname = f"light_id_pass_{i}"
                if hasattr(obj.octane, pname):
                    row.operator(f"light.toggle_{pname}", text=str(i), depress=_depress(mask_objs, pname))

        layout.operator("wm.url_open", text="加入 Blender 渲染QQ群").url = "https://qun.qq.com/universal-share/share?ac=1&authKey=2knFMW3lm2Gyb5sPJzMP0YJAKxl78D08wkzEGe%2FwciqzM9Lpfs0tJbR5VCdo2%2FEH&busi_data=eyJncm91cENvZGUiOiI3MDI0NDU4NjYiLCJ0b2tlbiI6InRJeDRFZTZoSkg2cTlYZHQzT0VJc3JVSmdaMGx6eitsNVNuRG9udUt5eXpYM0Uvdk9IaEtMcjlzcExycUE2SlgiLCJ1aW4iOiIxNzI0NzYwMDE4In0%3D&data=5G55VNM_JukqqhlN98yNlxKM0G3bHfFhrSnEvUQLm0jCPiEje0i9YrJUkYybBvmfWf4I2rspmee3cQGn010JHg&svctype=4&tempid=h5_group_info"

# —— Light Feedback 切换操作符 —— #
class LIGHT_OT_toggle_feedback(bpy.types.Operator):
    bl_idname = "light.toggle_feedback"
    bl_label = "Toggle Feedback"
    feedback_type: bpy.props.StringProperty()

    def execute(self, context):
        light = context.object.data
        if hasattr(light, self.feedback_type):
            cur = getattr(light, self.feedback_type)
            setattr(light, self.feedback_type, not cur)
            update_diffuse_feedback(light, context)
        return {'FINISHED'}

# —— Solo Light 切换 —— #
class LIGHT_OT_toggle_solo_light(bpy.types.Operator):
    bl_idname = "light.toggle_solo_light"
    bl_label  = "切换独显/恢复"

    def execute(self, context):
        cur = context.object
        if not cur or cur.type != 'LIGHT':
            self.report({'WARNING'}, "请选择灯光对象")
            return {'CANCELLED'}

        others = [o for o in bpy.data.objects if o.type=='LIGHT' and o!=cur]
        all_hidden = all(o.hide_viewport and o.hide_render for o in others)
        if all_hidden:
            for o in others + [cur]:
                o.hide_viewport = o.hide_render = False
            self.report({'INFO'}, "恢复所有灯光")
        else:
            for o in others:
                o.hide_viewport = o.hide_render = True
            cur.hide_viewport = cur.hide_render = False
            self.report({'INFO'}, f"独显: {cur.name}")
        return {'FINISHED'}

# —— 批量遮罩：切换指定遮罩通道（选中所有对象） —— #
class LIGHT_OT_batch_toggle_mask(bpy.types.Operator):
    bl_idname = "light.batch_toggle_mask"
    bl_label = "批量切换遮罩"
    prop_name: bpy.props.StringProperty()

    def execute(self, context):
        all_on = True
        objs = [o for o in context.selected_objects if hasattr(o, "octane") and hasattr(o.octane, self.prop_name)]
        if not objs:
            return {'CANCELLED'}
        for obj in objs:
            if not getattr(obj.octane, self.prop_name):
                all_on = False
                break
        target = not all_on
        for obj in objs:
            setattr(obj.octane, self.prop_name, target)
            obj.update_tag()
        context.view_layer.update()
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                area.tag_redraw()
        return {'FINISHED'}

# —— 批量遮罩：全开/全关选中对象的所有遮罩 —— #
class LIGHT_OT_batch_mask_all(bpy.types.Operator):
    bl_idname = "light.batch_mask_all"
    bl_label = "批量遮罩全开/全关"
    enable: bpy.props.BoolProperty(default=True)

    _mask_props = ["light_id_sunlight", "light_id_env"] + [f"light_id_pass_{i}" for i in range(1, 21)]

    def execute(self, context):
        for obj in context.selected_objects:
            if not hasattr(obj, "octane"):
                continue
            for pname in self._mask_props:
                if hasattr(obj.octane, pname):
                    setattr(obj.octane, pname, self.enable)
            obj.update_tag()
        context.view_layer.update()
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                area.tag_redraw()
        return {'FINISHED'}

# —— 批量设置灯光ID（选中所有灯光） —— #
class LIGHT_OT_batch_set_light_id(bpy.types.Operator):
    bl_idname = "light.batch_set_light_id"
    bl_label = "批量设置灯光ID"
    light_id: bpy.props.IntProperty(name="灯光ID", default=1, min=1, max=20)

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'LIGHT':
                obj.data.octane_diffuse_feedback_7 = self.light_id
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)

# —— 弹窗 —— #
class LIGHT_OT_popup(bpy.types.Operator):
    bl_idname = "light.popup_operator"
    bl_label  = "灯光控制"

    def draw(self, context):
        OC_PT_light_panel.draw(self, context)

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=400)

# —— 注册 Octane Toggle Operators —— #
octane_ops = [
    make_octane_toggle("light_id_sunlight", "Toggle Sunlight"),
    make_octane_toggle("light_id_env",       "Toggle Env"),
] + [
    make_octane_toggle(f"light_id_pass_{i}", f"Pass {i}") for i in range(1, 21)
]

# —— 注册 & 注销 —— #
addon_keymaps = []

def register():
    bpy.utils.register_class(OCAddonPreferences)
    bpy.utils.register_class(LIGHT_OT_toggle_feedback)
    bpy.utils.register_class(LIGHT_OT_toggle_solo_light)
    bpy.utils.register_class(LIGHT_OT_popup)
    bpy.utils.register_class(OC_PT_light_panel)
    bpy.utils.register_class(LIGHT_OT_batch_toggle_mask)
    bpy.utils.register_class(LIGHT_OT_batch_mask_all)
    bpy.utils.register_class(LIGHT_OT_batch_set_light_id)
    for op in octane_ops:
        bpy.utils.register_class(op)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        prefs = bpy.context.preferences.addons[__name__].preferences
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        
        # 注册弹窗快捷键
        for kmi in km.keymap_items:
            if kmi.idname == "light.popup_operator":
                km.keymap_items.remove(kmi)
        kmi = km.keymap_items.new(
            "light.popup_operator",
            prefs.popup_key,
            'PRESS',
            ctrl=prefs.popup_ctrl,
            shift=prefs.popup_shift,
            alt=prefs.popup_alt
        )
        addon_keymaps.append((km, kmi))

        # 注册灯光独显快捷键
        for kmi in km.keymap_items:
            if kmi.idname == "light.toggle_solo_light":
                km.keymap_items.remove(kmi)
        kmi = km.keymap_items.new(
            "light.toggle_solo_light",
            prefs.solo_key,
            'PRESS',
            ctrl=prefs.solo_ctrl,
            shift=prefs.solo_shift,
            alt=prefs.solo_alt
        )
        addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for op in reversed(octane_ops):
        bpy.utils.unregister_class(op)
    bpy.utils.unregister_class(LIGHT_OT_batch_set_light_id)
    bpy.utils.unregister_class(LIGHT_OT_batch_mask_all)
    bpy.utils.unregister_class(LIGHT_OT_batch_toggle_mask)
    bpy.utils.unregister_class(OC_PT_light_panel)
    bpy.utils.unregister_class(LIGHT_OT_popup)
    bpy.utils.unregister_class(LIGHT_OT_toggle_solo_light)
    bpy.utils.unregister_class(LIGHT_OT_toggle_feedback)
    bpy.utils.unregister_class(OCAddonPreferences)

if __name__ == "__main__":
    register()
