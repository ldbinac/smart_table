# 关系型数据库选型与多数据库支持分析

## 一、数据库核心特性对比

### 1.1 架构特性对比

| 特性维度 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **架构模式** | 客户端-服务器 (C/S) | 客户端-服务器 (C/S) | 嵌入式/文件型 |
| **进程模型** | 多进程 (每个连接一个进程) | 多线程 (线程池) | 单进程 (嵌入应用) |
| **存储引擎** | 单一存储引擎 (堆表) | 多引擎 (InnoDB/MyISAM等) | 单一虚拟数据库引擎 |
| **数据存储** | 表空间 + 数据文件 | 表空间/数据文件 | 单个磁盘文件 |
| **内存管理** | 共享缓冲区 (Shared Buffer) | 缓冲池 (Buffer Pool) | 页缓存 (Page Cache) |
| **连接方式** | TCP/IP, Unix Socket | TCP/IP, Unix Socket, 命名管道 | 直接 API 调用 |
| **部署复杂度** | 中等 (需独立部署) | 中等 (需独立部署) | 极低 (零配置) |

### 1.2 性能表现对比

```
性能指标雷达图

                    读性能
                      │
         并发处理 ───┼─── 写性能
                      │
              SQLite ●────● MySQL
                      │
                   PostgreSQL
                      │
        大数据量 ─────┼───── 小数据量
                      │
                   复杂查询
```

| 性能指标 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **读性能 (简单查询)** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **写性能 (INSERT)** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **复杂查询** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **并发读取** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **并发写入** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **大数据量 (>100GB)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **小数据量 (<1GB)** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **启动时间** | 较慢 (秒级) | 中等 | 极快 (毫秒级) |
| **内存占用** | 较高 (100MB+) | 中等 (50MB+) | 极低 (<1MB) |

**详细性能数据：**

| 测试场景 | PostgreSQL | MySQL (InnoDB) | SQLite |
|----------|------------|----------------|--------|
| 单条 INSERT | 2-5 ms | 1-3 ms | 0.1-0.5 ms |
| 批量 INSERT (1000条) | 200-500 ms | 100-300 ms | 50-200 ms |
| 简单 SELECT | 1-3 ms | 0.5-2 ms | 0.1-0.5 ms |
| 复杂 JOIN (3表) | 10-50 ms | 20-100 ms | 100-500 ms |
| 并发连接 (100+) | 优秀 | 优秀 | 不适用 |

### 1.3 功能支持对比

#### SQL 标准兼容性

| 功能特性 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **SQL 标准兼容性** | ⭐⭐⭐⭐⭐ (最标准) | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **窗口函数** | ✅ 完整支持 | ✅ 8.0+ 支持 | ✅ 3.25+ 支持 |
| **CTE (公用表表达式)** | ✅ 完整支持 | ✅ 8.0+ 支持 | ✅ 3.8.3+ 支持 |
| **递归查询** | ✅ 完整支持 | ✅ 8.0+ 支持 | ✅ 3.8.3+ 支持 |
| **JSON 支持** | ✅ JSON/JSONB | ✅ JSON | ✅ JSON1 扩展 |
| **数组类型** | ✅ 原生支持 | ❌ 不支持 | ❌ 不支持 |
| **自定义类型** | ✅ 完整支持 | ❌ 有限支持 | ❌ 不支持 |
| **全文搜索** | ✅ 内置 | ✅ 插件 | ✅ FTS 扩展 |
| **地理信息 (GIS)** | ✅ PostGIS | ✅ 插件 | ✅ Spatialite |
| **存储过程** | ✅ PL/pgSQL, PL/Python等 | ✅ 有限支持 | ❌ 不支持 |
| **触发器** | ✅ 行级/语句级 | ✅ 行级 | ✅ 行级 |
| **外键约束** | ✅ 完整支持 | ✅ InnoDB支持 | ✅ 完整支持 |
| **检查约束** | ✅ 完整支持 | ✅ 8.0.16+ | ✅ 3.3.0+ |

#### 高级功能对比

| 高级特性 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **分区表** | ✅ 声明式分区 | ✅ 分区 | ❌ 不支持 |
| **并行查询** | ✅ 9.6+ | ✅ 8.0+ | ❌ 不支持 |
| **逻辑复制** | ✅ 内置 | ✅ 8.0+ | ❌ 不支持 |
| **物理复制** | ✅ 流复制 | ✅ 半同步 | ❌ 不支持 |
| **外部数据包装器** | ✅ FDW | ✅ 有限 | ❌ 不支持 |
| **物化视图** | ✅ 内置 | ❌ 不支持 | ❌ 不支持 |
| **表继承** | ✅ 内置 | ❌ 不支持 | ❌ 不支持 |

### 1.4 适用场景对比

```
适用场景矩阵

                    企业级应用
                         │
    数据仓库 ────────────┼──────────── 嵌入式应用
                         │
              PostgreSQL ●
                         │
         MySQL ──────────┼───────── SQLite
                         │
    Web 应用 ────────────┼────────── 移动应用
                         │
                    分析型应用
```

| 应用场景 | 推荐数据库 | 理由 |
|----------|-----------|------|
| **企业级核心业务** | PostgreSQL | 强一致性、复杂查询、扩展性强 |
| **高并发 Web 应用** | MySQL | 读写性能优秀、连接池成熟 |
| **嵌入式/移动应用** | SQLite | 零配置、单文件、资源占用低 |
| **数据分析/BI** | PostgreSQL | 窗口函数、CTE、复杂查询优化 |
| **原型/MVP 开发** | SQLite → PostgreSQL | 快速启动，后期迁移 |
| **微服务架构** | PostgreSQL/MySQL | 容器化友好、云原生支持 |
| **边缘计算/IoT** | SQLite | 资源受限环境、离线优先 |
| **金融交易系统** | PostgreSQL | ACID、事务隔离级别完善 |

### 1.5 扩展性对比

| 扩展维度 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **垂直扩展** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **水平扩展 (读写分离)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ 不支持 |
| **水平扩展 (分片)** | ⭐⭐⭐⭐ (Citus) | ⭐⭐⭐⭐ (MyCAT等) | ❌ 不支持 |
| **云原生支持** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **插件生态** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **扩展开发** | C, Python, 等 | C/C++ | C |

### 1.6 事务处理能力对比

| 事务特性 | PostgreSQL | MySQL (InnoDB) | SQLite |
|----------|------------|----------------|--------|
| **ACID 支持** | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| **隔离级别** | 4种 (含 Serializable) | 4种 | 3种 (无 Serializable) |
| **默认隔离级别** | Read Committed | Repeatable Read | Serializable |
| **MVCC 实现** | 多版本并发控制 | 多版本并发控制 | 回滚日志 (WAL) |
| **事务回滚** | 完整支持 | 完整支持 | 完整支持 |
| **保存点 (Savepoint)** | ✅ 支持 | ✅ 支持 | ✅ 支持 |
| **两阶段提交 (2PC)** | ✅ 支持 | ✅ 支持 | ❌ 不支持 |
| **分布式事务 (XA)** | ✅ 支持 | ✅ 支持 | ❌ 不支持 |

**事务性能对比：**

| 测试场景 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| 单事务 TPS | 10,000+ | 15,000+ | 50,000+ (单连接) |
| 多连接 TPS | 50,000+ | 80,000+ | 不适用 |
| 长事务影响 | 较小 (MVCC) | 较小 (MVCC) | 较大 (锁) |

### 1.7 并发控制机制对比

| 并发特性 | PostgreSQL | MySQL (InnoDB) | SQLite |
|----------|------------|----------------|--------|
| **锁粒度** | 行级锁 | 行级锁 | 数据库级锁 |
| **锁模式** | 共享锁、排他锁、意向锁 | 共享锁、排他锁、间隙锁 | 共享锁、排他锁 |
| **死锁检测** | ✅ 自动检测 | ✅ 自动检测 | ❌ 无 (超时) |
| **锁等待超时** | ✅ 可配置 | ✅ 可配置 | ✅ 可配置 |
| **并发写入** | 优秀 (MVCC) | 优秀 (MVCC) | 受限 (WAL 模式改善) |
| **读不阻塞写** | ✅ 支持 | ✅ 支持 | ✅ 支持 (WAL) |
| **写不阻塞读** | ✅ 支持 | ✅ 支持 | ✅ 支持 (WAL) |

**SQLite 并发模式：**

| 模式 | 特点 | 适用场景 |
|------|------|----------|
| **DELETE (默认)** | 每次写操作后删除日志 | 低并发 |
| **TRUNCATE** | 截断日志文件 | 中等并发 |
| **PERSIST** | 保留日志文件 | 频繁写入 |
| **MEMORY** | 日志在内存中 | 临时数据 |
| **WAL (推荐)** | 写前日志，读写并发 | 高并发读取 |
| **OFF** | 无日志，最快 | 临时/测试 |

### 1.8 数据完整性约束对比

| 约束类型 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **主键 (PRIMARY KEY)** | ✅ 支持 | ✅ 支持 | ✅ 支持 |
| **唯一约束 (UNIQUE)** | ✅ 支持 | ✅ 支持 | ✅ 支持 |
| **外键 (FOREIGN KEY)** | ✅ 支持 | ✅ InnoDB | ✅ 3.6.19+ |
| **非空 (NOT NULL)** | ✅ 支持 | ✅ 支持 | ✅ 支持 |
| **默认值 (DEFAULT)** | ✅ 支持 | ✅ 支持 | ✅ 支持 |
| **检查约束 (CHECK)** | ✅ 支持 | ✅ 8.0.16+ | ✅ 3.3.0+ |
| **排除约束 (EXCLUDE)** | ✅ 支持 | ❌ 不支持 | ❌ 不支持 |
| **域 (DOMAIN)** | ✅ 支持 | ❌ 不支持 | ❌ 不支持 |
| **断言 (ASSERTION)** | ❌ 不支持 | ❌ 不支持 | ❌ 不支持 |

### 1.9 管理维护复杂度对比

| 维护维度 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **安装配置** | ⭐⭐⭐ (中等) | ⭐⭐⭐ (中等) | ⭐ (极简) |
| **备份恢复** | ⭐⭐⭐⭐ (pg_dump/pg_basebackup) | ⭐⭐⭐⭐ (mysqldump/xtrabackup) | ⭐⭐⭐⭐⭐ (文件复制) |
| **监控调优** | ⭐⭐⭐ (复杂) | ⭐⭐⭐ (中等) | ⭐⭐⭐⭐ (简单) |
| **版本升级** | ⭐⭐⭐ (需谨慎) | ⭐⭐⭐⭐ (较简单) | ⭐⭐⭐⭐⭐ (替换文件) |
| **高可用配置** | ⭐⭐ (复杂) | ⭐⭐⭐ (中等) | N/A |
| **性能调优** | ⭐⭐⭐ (参数多) | ⭐⭐⭐⭐ (较简单) | ⭐⭐⭐⭐⭐ (极少参数) |
| **故障排查** | ⭐⭐⭐ (工具多) | ⭐⭐⭐⭐ (文档丰富) | ⭐⭐⭐⭐⭐ (简单) |
| **运维成本** | 高 | 中等 | 极低 |

---

## 二、多数据库支持可行性分析

### 2.1 技术方案概述

```
多数据库支持架构

┌─────────────────────────────────────────────────────────────────┐
│                          应用层                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   ORM 层    │  │  数据库抽象  │  │      查询构建器         │ │
│  │ SQLAlchemy  │  │   接口层    │  │    (Query Builder)      │ │
│  │  Sequelize  │  │             │  │                         │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│         └────────────────┴──────────────────────┘               │
│                         │                                       │
│              ┌──────────▼──────────┐                           │
│              │   数据库适配器工厂   │                           │
│              │   (Adapter Factory) │                           │
│              └──────────┬──────────┘                           │
└─────────────────────────┼───────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ PostgreSQL │  │   MySQL    │  │   SQLite   │
   │   适配器    │  │   适配器    │  │   适配器    │
   └────────────┘  └────────────┘  └────────────┘
```

### 2.2 实现方案对比

| 实现方案 | 复杂度 | 灵活性 | 性能 | 维护成本 |
|----------|--------|--------|------|----------|
| **ORM 抽象层** | 低 | 高 | 中等 | 低 |
| **数据库适配器模式** | 中等 | 高 | 高 | 中等 |
| **SQL 方言转换** | 高 | 中等 | 中等 | 高 |
| **微服务拆分** | 高 | 高 | 高 | 高 |

### 2.3 SQL 语法差异分析

#### 数据类型差异

| 数据类型 | PostgreSQL | MySQL | SQLite | 兼容性策略 |
|----------|------------|-------|--------|-----------|
| **字符串 (变长)** | VARCHAR(n) | VARCHAR(n) | TEXT | 统一使用 VARCHAR |
| **大文本** | TEXT | LONGTEXT | TEXT | 统一使用 TEXT |
| **整数** | INTEGER, BIGINT | INT, BIGINT | INTEGER | 统一使用 INTEGER |
| **浮点数** | REAL, DOUBLE | FLOAT, DOUBLE | REAL | 统一使用 REAL |
| **定点数** | NUMERIC(p,s) | DECIMAL(p,s) | NUMERIC | 统一使用 NUMERIC |
| **布尔** | BOOLEAN | BOOLEAN (TINYINT) | INTEGER (0/1) | ORM 层转换 |
| **日期时间** | TIMESTAMP | DATETIME | TEXT/TIMESTAMP | 统一使用 TIMESTAMP |
| **JSON** | JSON, JSONB | JSON | TEXT (JSON1) | ORM 层封装 |
| **UUID** | UUID | CHAR(36) | TEXT | ORM 层生成 |
| **二进制** | BYTEA | BLOB | BLOB | 统一使用 BLOB |
| **数组** | ARRAY | JSON | JSON | 避免使用或 JSON 模拟 |
| **枚举** | ENUM | ENUM | TEXT + CHECK | 使用查找表替代 |

#### SQL 语法差异

| 语法特性 | PostgreSQL | MySQL | SQLite | 解决方案 |
|----------|------------|-------|--------|----------|
| **字符串连接** | \|\| | CONCAT() | \|\| | 使用 CONCAT() 函数 |
| **LIMIT/OFFSET** | LIMIT/OFFSET | LIMIT/OFFSET | LIMIT/OFFSET | 语法一致 |
| **分页语法** | LIMIT/OFFSET | LIMIT offset, count | LIMIT/OFFSET | 统一使用 LIMIT/OFFSET |
| **自增主键** | SERIAL | AUTO_INCREMENT | INTEGER PRIMARY KEY | ORM 层处理 |
| **当前时间** | NOW() | NOW() | datetime('now') | 使用 ORM 函数 |
| **随机数** | RANDOM() | RAND() | RANDOM() | 封装随机函数 |
| **字符串长度** | LENGTH() | LENGTH()/CHAR_LENGTH() | LENGTH() | 统一使用 LENGTH() |
| **子查询限制** | 无限制 | 无限制 | 有限制 | 避免复杂子查询 |
| **递归 CTE** | 完整支持 | 8.0+ 支持 | 3.8.3+ 支持 | 版本检查 |
| **窗口函数** | 完整支持 | 8.0+ 支持 | 3.25+ 支持 | 版本检查 |
| **UPSERT** | ON CONFLICT | ON DUPLICATE KEY | ON CONFLICT | 使用 ORM 的 merge |
| **RETURNING** | ✅ 支持 | 不支持 | 3.35+ 支持 | 使用触发器或查询 |

### 2.4 潜在挑战分析

#### 挑战一：SQL 语法兼容性

```python
# 示例：处理不同数据库的 SQL 差异
class SQLDialect:
    """SQL 方言基类"""
    
    def limit_offset(self, limit, offset):
        raise NotImplementedError
    
    def current_timestamp(self):
        raise NotImplementedError
    
    def concat(self, *args):
        raise NotImplementedError

class PostgreSQLDialect(SQLDialect):
    def limit_offset(self, limit, offset):
        return f"LIMIT {limit} OFFSET {offset}"
    
    def current_timestamp(self):
        return "NOW()"
    
    def concat(self, *args):
        return " || ".join(args)

class MySQLDialect(SQLDialect):
    def limit_offset(self, limit, offset):
        return f"LIMIT {offset}, {limit}"
    
    def current_timestamp(self):
        return "NOW()"
    
    def concat(self, *args):
        return f"CONCAT({', '.join(args)})"

class SQLiteDialect(SQLDialect):
    def limit_offset(self, limit, offset):
        return f"LIMIT {limit} OFFSET {offset}"
    
    def current_timestamp(self):
        return "datetime('now')"
    
    def concat(self, *args):
        return " || ".join(args)
```

#### 挑战二：事务一致性

| 事务差异 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **默认隔离级别** | Read Committed | Repeatable Read | Serializable |
| **行为差异** | 可能出现不可重复读 | 幻读保护 | 严格串行化 |
| **影响** | 并发性能好 | 平衡 | 并发性能差 |

**解决方案：**
1. 统一使用显式事务隔离级别设置
2. 在应用层实现乐观锁
3. 对于 SQLite，使用 WAL 模式提升并发

#### 挑战三：性能优化差异

| 优化维度 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **索引类型** | B-tree, Hash, GiST, GIN, BRIN | B-tree, Hash, Full-text | B-tree, 部分索引 |
| **查询优化器** | 成本基于优化器 | 成本基于优化器 | 基于规则优化器 |
| **统计信息** | 自动收集 | 自动收集 | 有限 |
| **执行计划** | EXPLAIN ANALYZE | EXPLAIN | EXPLAIN QUERY PLAN |

**解决方案：**
1. 避免依赖特定数据库的优化特性
2. 使用通用的索引策略
3. 定期进行性能测试

#### 挑战四：功能限制

| 功能限制 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **ALTER TABLE** | 完整支持 | 部分操作锁表 | 有限支持 |
| **外键约束检查** | 默认开启 | 默认开启 | 3.6.19+ 默认关闭 |
| **类型检查** | 严格 | 宽松 (类型转换) | 动态类型 |
| **并发写入** | 优秀 | 优秀 | 受限 |

**解决方案：**
1. 设计时考虑最低功能集
2. 使用 ORM 处理类型转换
3. 对于 SQLite，显式启用外键检查

### 2.5 维护成本分析

```
维护成本增长模型

成本
 │
 │    单数据库
 │      ─────
 │           ╲
 │            ╲  多数据库
 │             ╲ ─────
 │              ╲
 │               ╲
 └─────────────────────────────►
   开发    测试    运维    时间

成本增长因素：
- 开发复杂度: +30-50%
- 测试工作量: +50-100%
- 运维难度: +20-30%
- 文档维护: +40-60%
```

| 成本维度 | 单数据库 | 多数据库支持 | 增长比例 |
|----------|----------|--------------|----------|
| **开发成本** | 基准 | +30-50% | 需要适配层 |
| **测试成本** | 基准 | +50-100% | 多环境测试 |
| **运维成本** | 基准 | +20-30% | 监控告警 |
| **文档成本** | 基准 | +40-60% | 多版本文档 |
| **故障排查** | 基准 | +50-80% | 多环境复现 |
| **培训成本** | 基准 | +30-40% | 团队技能 |

---

## 三、实施建议与最佳实践

### 3.1 推荐架构方案

#### 方案一：ORM 抽象层（推荐）

```python
# 使用 SQLAlchemy 实现多数据库支持
from sqlalchemy import create_engine, Column, String, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Record(Base):
    __tablename__ = 'records'
    
    id = Column(String(36), primary_key=True)
    table_id = Column(String(36), nullable=False)
    values = Column(JSON)  # SQLAlchemy 自动处理不同数据库的 JSON 类型
    created_at = Column(DateTime, default=datetime.utcnow)

# 数据库连接工厂
class DatabaseFactory:
    @staticmethod
    def create_engine(db_type, connection_string):
        if db_type == 'postgresql':
            return create_engine(connection_string, 
                               pool_size=20,
                               max_overflow=0)
        elif db_type == 'mysql':
            return create_engine(connection_string,
                               pool_size=20,
                               pool_recycle=3600)
        elif db_type == 'sqlite':
            return create_engine(connection_string,
                               connect_args={'check_same_thread': False})
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
```

**优点：**
- 开发成本低
- 社区支持好
- 自动处理大部分差异

**缺点：**
- 性能略低于原生 SQL
- 复杂查询受限

#### 方案二：Repository 模式 + 适配器

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class RecordRepository(ABC):
    """记录仓库抽象接口"""
    
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def create(self, data: Dict) -> Dict:
        pass
    
    @abstractmethod
    def update(self, id: str, data: Dict) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        pass
    
    @abstractmethod
    def list_by_table(self, table_id: str, page: int, page_size: int) -> List[Dict]:
        pass

class PostgreSQLRecordRepository(RecordRepository):
    """PostgreSQL 实现"""
    
    def __init__(self, connection):
        self.conn = connection
    
    def get_by_id(self, id: str) -> Optional[Dict]:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, table_id, values, created_at 
                FROM records WHERE id = %s
            """, (id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def create(self, data: Dict) -> Dict:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO records (id, table_id, values, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id, table_id, values, created_at
            """, (data['id'], data['table_id'], json.dumps(data['values'])))
            row = cur.fetchone()
            self.conn.commit()
            return dict(row)

class MySQLRecordRepository(RecordRepository):
    """MySQL 实现"""
    
    def __init__(self, connection):
        self.conn = connection
    
    def create(self, data: Dict) -> Dict:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO records (id, table_id, values, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (data['id'], data['table_id'], json.dumps(data['values'])))
            self.conn.commit()
            # MySQL 不支持 RETURNING，需要重新查询
            return self.get_by_id(data['id'])

class SQLiteRecordRepository(RecordRepository):
    """SQLite 实现"""
    
    def __init__(self, connection):
        self.conn = connection
    
    def create(self, data: Dict) -> Dict:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO records (id, table_id, values, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (data['id'], data['table_id'], json.dumps(data['values'])))
            self.conn.commit()
            return self.get_by_id(data['id'])

# 仓库工厂
class RepositoryFactory:
    @staticmethod
    def create_record_repository(db_type: str, connection):
        repositories = {
            'postgresql': PostgreSQLRecordRepository,
            'mysql': MySQLRecordRepository,
            'sqlite': SQLiteRecordRepository
        }
        return repositories[db_type](connection)
```

**优点：**
- 完全控制 SQL 生成
- 性能最优
- 灵活性高

**缺点：**
- 开发成本高
- 代码重复

### 3.2 数据库选择决策树

```
数据库选择决策
    │
    ├─► 是否需要嵌入式部署?
    │       │
    │       ├─ 是 ─► 【选择 SQLite】
    │       │         (移动应用、桌面应用、IoT)
    │       │
    │       └─ 否
    │               │
    │               └─► 是否需要复杂查询/分析?
    │                       │
    │                       ├─ 是 ─► 【选择 PostgreSQL】
    │                       │         (数据仓库、GIS、复杂业务)
    │                       │
    │                       └─ 否
    │                               │
    │                               └─► 是否追求极致读写性能?
    │                                       │
    │                                       ├─ 是 ─► 【选择 MySQL】
    │                                       │         (Web 应用、高并发)
    │                                       │
    │                                       └─ 否 ─► 【选择 PostgreSQL】
    │                                                 (通用、功能丰富)
```

### 3.3 多数据库支持最佳实践

#### 1. 配置管理

```yaml
# config/database.yaml
databases:
  development:
    type: sqlite
    url: sqlite:///dev.db
    
  testing:
    type: sqlite
    url: sqlite:///:memory:
    
  staging:
    type: postgresql
    url: postgresql://user:pass@localhost:5432/staging
    pool_size: 10
    
  production:
    type: postgresql  # 或 mysql
    url: ${DATABASE_URL}
    pool_size: 20
    max_overflow: 10
    
  edge:
    type: sqlite
    url: sqlite:///edge.db
    pragmas:
      journal_mode: WAL
      synchronous: NORMAL
```

#### 2. 迁移策略

```python
# 使用 Alembic 处理多数据库迁移
# alembic/env.py

def run_migrations_online():
    """运行在线迁移"""
    db_type = config.get_main_option('db_type')
    
    if db_type == 'sqlite':
        # SQLite 特殊处理
        def process_revision_directives(context, revision, directives):
            # SQLite 不支持某些 ALTER 操作
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
    else:
        process_revision_directives = None
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

#### 3. 测试策略

```python
# 多数据库测试
import pytest

class TestRecordRepository:
    @pytest.fixture(params=['sqlite', 'postgresql', 'mysql'])
    def repository(self, request):
        """参数化测试不同数据库"""
        db_type = request.param
        connection = create_test_connection(db_type)
        return RepositoryFactory.create_record_repository(db_type, connection)
    
    def test_create_record(self, repository):
        """测试创建记录"""
        data = {'id': 'test-1', 'table_id': 'table-1', 'values': {'name': 'Test'}}
        result = repository.create(data)
        assert result['id'] == 'test-1'
    
    def test_json_field(self, repository):
        """测试 JSON 字段"""
        complex_data = {
            'id': 'test-2',
            'table_id': 'table-1',
            'values': {
                'nested': {'key': 'value'},
                'array': [1, 2, 3],
                'null': None
            }
        }
        result = repository.create(complex_data)
        assert result['values']['nested']['key'] == 'value'
```

#### 4. 性能监控

```python
# 数据库性能监控
from functools import wraps
import time

class DatabaseMetrics:
    def __init__(self):
        self.query_times = {}
        self.error_counts = {}
    
    def record_query_time(self, db_type: str, operation: str, duration: float):
        key = f"{db_type}.{operation}"
        if key not in self.query_times:
            self.query_times[key] = []
        self.query_times[key].append(duration)
    
    def get_stats(self):
        stats = {}
        for key, times in self.query_times.items():
            stats[key] = {
                'count': len(times),
                'avg': sum(times) / len(times),
                'max': max(times),
                'min': min(times)
            }
        return stats

def monitor_query(operation: str):
    """查询监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start = time.time()
            try:
                result = func(self, *args, **kwargs)
                duration = time.time() - start
                metrics.record_query_time(self.db_type, operation, duration)
                return result
            except Exception as e:
                metrics.error_counts[f"{self.db_type}.{operation}"] = \
                    metrics.error_counts.get(f"{self.db_type}.{operation}", 0) + 1
                raise
        return wrapper
    return decorator
```

### 3.4 风险评估与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| **SQL 兼容性问题** | 高 | 中 | 使用 ORM；避免原生 SQL；充分测试 |
| **性能不一致** | 高 | 高 | 基准测试；优化策略差异化 |
| **数据迁移困难** | 中 | 低 | 制定迁移方案；数据验证工具 |
| **团队技能要求** | 中 | 高 | 培训；文档；代码审查 |
| **维护成本超支** | 高 | 中 | 定期评估；逐步简化 |
| **Bug 排查复杂** | 中 | 高 | 完善日志；监控告警；复现环境 |

### 3.5 实施路线图

```
多数据库支持实施路线图

Phase 1: 基础架构 (2-3 周)
├── 选择 ORM 框架 (SQLAlchemy/Prisma)
├── 设计数据库抽象层
├── 实现基础 CRUD 操作
└── 建立测试框架

Phase 2: 核心功能 (3-4 周)
├── 实现所有实体模型
├── 处理 SQL 差异
├── 实现事务管理
└── 性能基准测试

Phase 3: 高级功能 (2-3 周)
├── 复杂查询支持
├── 全文搜索
├── 数据迁移工具
└── 监控告警

Phase 4: 优化与文档 (1-2 周)
├── 性能优化
├── 完善文档
├── 团队培训
└── 生产上线

总计: 8-12 周
```

---

## 四、针对 SmartTable 的具体建议

### 4.1 推荐方案

**主推荐：PostgreSQL 单数据库**

理由：
1. SmartTable 需要复杂的 JSON 操作和公式计算
2. 多维表格需要强大的查询能力（筛选、排序、分组）
3. 未来可能需要全文搜索和 GIS 功能
4. 企业级应用对数据一致性要求高

**备选：PostgreSQL + SQLite 混合**

场景：
- 主服务使用 PostgreSQL
- 边缘/离线场景使用 SQLite
- 通过同步机制保持数据一致

### 4.2 不建议的方案

**不推荐：同时支持三种数据库**

原因：
1. 维护成本过高（+50-100%）
2. SmartTable 的复杂查询在 SQLite 上性能差
3. MySQL 的 JSON 功能不如 PostgreSQL 完善
4. 团队需要掌握三种数据库的优化技巧

### 4.3 技术选型矩阵

| 场景 | 推荐数据库 | 理由 |
|------|-----------|------|
| **SaaS 多租户** | PostgreSQL | 模式隔离、性能优秀 |
| **私有化部署** | PostgreSQL | 功能完整、运维成熟 |
| **边缘计算** | SQLite | 零配置、资源占用低 |
| **移动端同步** | SQLite | 离线优先、同步到云端 |
| **数据分析** | PostgreSQL | 窗口函数、CTE、复杂查询 |

---

## 五、总结

### 5.1 数据库选型结论

| 评估维度 | PostgreSQL | MySQL | SQLite |
|----------|------------|-------|--------|
| **SmartTable 匹配度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **功能完整性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **性能表现** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **运维成本** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **扩展性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

### 5.2 多数据库支持结论

| 方案 | 可行性 | 推荐度 | 适用场景 |
|------|--------|--------|----------|
| **单数据库 (PostgreSQL)** | ✅ 高 | ⭐⭐⭐⭐⭐ | 通用场景 |
| **主从混合 (PG + SQLite)** | ✅ 中 | ⭐⭐⭐⭐ | 边缘计算 |
| **三数据库全支持** | ⚠️ 低 | ⭐⭐ | 不推荐 |

### 5.3 最终建议

**短期（当前阶段）：**
- 使用 PostgreSQL 作为唯一数据库
- 利用 JSONB 存储动态字段值
- 使用窗口函数实现高级查询

**长期（未来扩展）：**
- 考虑 PostgreSQL + SQLite 混合架构
- 实现数据同步机制
- 支持离线优先的边缘场景

**避免：**
- 同时支持三种数据库
- 过度设计多数据库抽象层
- 在 SQLite 上实现复杂分析功能

---

*文档版本：v1.0*
*最后更新：2026-04-03*
