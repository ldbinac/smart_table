"""
跨模块前向引用注入工具

PyArmor 加密后，模块加载顺序不确定，group mixin 文件里硬编码引用主类
（如 `FieldService.VALID_FIELD_TYPES`）会触发 NameError。

在主 Service 文件末尾（类定义完成之后）调用 inject()，
把主类注入到所有引用它的 group 模块的全局命名空间，
这样无论加密环境下 import 顺序如何，运行时都能找到。

用法（在主 Service 文件末尾，FieldService 类定义完之后）：
    from app.services._inject import inject_main_class
    inject_main_class(FieldService,
        'field_service_group01', 'field_service_group02', 'field_service_group03')
"""
import logging

logger = logging.getLogger(__name__)


def inject_main_class(main_class, *group_module_names):
    """把 main_class 反向注入到指定的 group 模块。
    
    Args:
        main_class: 主 Service 类对象（已完成定义）
        *group_module_names: 需要注入的 group 模块名（不含路径和 .py 后缀）
    
    Example:
        inject_main_class(LinkService, 'link_service_group01', 'link_service_group02')
    """
    class_name = main_class.__name__
    injected = []
    missing = []
    
    for gname in group_module_names:
        full_path = f'app.services.{gname}'
        try:
            import importlib
            mod = importlib.import_module(full_path)
            setattr(mod, class_name, main_class)
            injected.append(gname)
        except ImportError:
            # group 模块可能不存在（可选功能），非致命
            missing.append(gname)
        except Exception as e:
            logger.debug(f'[inject_main_class] 注入 {class_name} -> {gname} 失败: {e}')
            missing.append(gname)
    
    if injected:
        logger.debug(
            f'[inject] ✅ {class_name} 已注入到 {len(injected)} 个 group 模块: {injected}'
        )
    if missing:
        logger.debug(
            f'[inject] ⚠️  {class_name} 未找到 {len(missing)} 个 group 模块（可能不存在）: {missing}'
        )
