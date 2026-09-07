"""
插件 manifest.json 的 JSON Schema（Draft-07）
安装/升级时由 PluginService 使用 jsonschema 校验。
"""

MANIFEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "SmartTable Plugin Manifest",
    "type": "object",
    "required": ["id", "name", "version", "type", "apiVersion", "engines",
                 "entry", "permissions"],
    "additionalProperties": False,
    "properties": {
        "id": {
            "type": "string",
            "minLength": 3,
            "maxLength": 200,
            "pattern": "^[a-z0-9][a-z0-9.-]+$",
            "description": "插件 ID（反向域名格式），全局唯一，安装后不可变更"
        },
        "name": {"type": "string", "minLength": 2, "maxLength": 50},
        "description": {"type": "string", "maxLength": 500},
        "icon": {"type": "string", "maxLength": 500},
        "author": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "maxLength": 100},
                "url": {"type": "string", "maxLength": 500},
                "email": {"type": "string", "maxLength": 200}
            }
        },
        "version": {
            "type": "string",
            "pattern": r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
                       r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$",
            "description": "semver 版本号"
        },
        "type": {"enum": ["ui", "script"]},
        "apiVersion": {
            "type": "string",
            "description": "宿主插件 API 大版本号，当前支持 '1'"
        },
        "engines": {
            "type": "object",
            "required": ["smarttable"],
            "additionalProperties": False,
            "properties": {
                "smarttable": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "宿主版本兼容范围（npm range 语法子集：> >= < <= = ^ ~ *）"
                }
            }
        },
        "entry": {
            "type": "string",
            "maxLength": 500,
            "description": "入口文件相对路径：ui 为 .js，script 为 .py"
        },
        "permissions": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "records": {"enum": ["read", "write"]},
                "tables": {"enum": ["read", "write"]},
                "storage": {"type": "boolean"},
                "network": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 200},
                    "maxItems": 20,
                    "description": "允许请求的域名白名单（首期协议预留）"
                }
            },
            "description": "对象式分级权限声明，未声明默认拒绝"
        },
        "extensionPoints": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "required": ["type", "title"],
                "additionalProperties": False,
                "properties": {
                    "type": {
                        "enum": ["toolbar-button", "side-panel",
                                 "base-menu", "record-detail-block"]
                    },
                    "title": {"type": "string", "minLength": 1, "maxLength": 50},
                    "icon": {"type": "string", "maxLength": 50,
                             "description": "Element Plus 图标名（宿主渲染）"}
                }
            }
        },
        "configSchema": {
            "type": "object",
            "description": "插件配置结构定义（JSON Schema Draft-07 子集）"
        },
        "script": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 300,
                    "description": "脚本超时秒数，默认 30，上限 300"
                }
            }
        }
    }
}
