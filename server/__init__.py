"""
Evolution System - 进化系统模块化包

架构：
- 常驻内存模块系统
- 共享缓存层（Redis + LanceDB）
- 共享模型（BGE 512 维）
- 支持 HTTP/直接导入/CLI 三种调用方式

使用示例：
    from evolution import EvolutionSystem
    
    evolution = EvolutionSystem()
    result = evolution.think("分析问题")
    result = evolution.learn("学习内容", material={...})
"""

from .core import EvolutionSystem
from .cache import CacheLayer

__version__ = '1.0.0'
__all__ = ['EvolutionSystem', 'CacheLayer']
