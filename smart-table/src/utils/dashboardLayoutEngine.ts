import type { WidgetConfig } from '@/db/services/dashboardService'

export type LayoutType = 'grid' | 'free'

export interface GridPosition {
  x: number
  y: number
  w: number
  h: number
}

export interface FreePosition {
  x: number
  y: number
  w: number
  h: number
  z: number
}

export interface LayoutConfig {
  type: LayoutType
  columns: number
  rowHeight: number
  gap: number
  padding: number
  containerWidth: number
  containerHeight?: number
}

export interface SnapResult {
  x: number
  y: number
  w: number
  h: number
  snapped: boolean
}

export interface CollisionResult {
  hasCollision: boolean
  collidingWidgets: string[]
  suggestedPosition?: GridPosition
}

export class DashboardLayoutEngine {
  private config: LayoutConfig
  private widgets: Map<string, WidgetConfig> = new Map()

  constructor(config: Partial<LayoutConfig> = {}) {
    this.config = {
      type: 'grid',
      columns: 12,
      rowHeight: 80,
      gap: 16,
      padding: 24,
      containerWidth: 1200,
      ...config,
    }
  }

  // 更新配置
  updateConfig(config: Partial<LayoutConfig>): void {
    this.config = { ...this.config, ...config }
  }

  // 获取配置
  getConfig(): LayoutConfig {
    return { ...this.config }
  }

  // 注册组件
  registerWidget(widget: WidgetConfig): void {
    this.widgets.set(widget.id, widget)
  }

  // 注销组件
  unregisterWidget(widgetId: string): void {
    this.widgets.delete(widgetId)
  }

  // 获取所有组件
  getWidgets(): WidgetConfig[] {
    return Array.from(this.widgets.values())
  }

  // 计算网格单元格宽度
  private getCellWidth(): number {
    const totalGap = (this.config.columns - 1) * this.config.gap
    const availableWidth =
      this.config.containerWidth - this.config.padding * 2 - totalGap
    return availableWidth / this.config.columns
  }

  // 像素位置转换为网格位置
  pixelToGrid(
    pixelX: number,
    pixelY: number,
    pixelW: number,
    pixelH: number
  ): GridPosition {
    const cellWidth = this.getCellWidth()

    const x = Math.round(
      (pixelX - this.config.padding) / (cellWidth + this.config.gap)
    )
    const y = Math.round(
      (pixelY - this.config.padding) /
        (this.config.rowHeight + this.config.gap)
    )
    const w = Math.round(
      (pixelW + this.config.gap) / (cellWidth + this.config.gap)
    )
    const h = Math.round(
      (pixelH + this.config.gap) / (this.config.rowHeight + this.config.gap)
    )

    return {
      x: Math.max(0, Math.min(x, this.config.columns - 1)),
      y: Math.max(0, y),
      w: Math.max(1, Math.min(w, this.config.columns)),
      h: Math.max(1, h),
    }
  }

  // 网格位置转换为像素位置
  gridToPixel(position: GridPosition): {
    x: number
    y: number
    w: number
    h: number
  } {
    const cellWidth = this.getCellWidth()

    return {
      x:
        this.config.padding +
        position.x * (cellWidth + this.config.gap),
      y:
        this.config.padding +
        position.y * (this.config.rowHeight + this.config.gap),
      w: position.w * cellWidth + (position.w - 1) * this.config.gap,
      h:
        position.h * this.config.rowHeight +
        (position.h - 1) * this.config.gap,
    }
  }

  // 吸附到网格
  snapToGrid(
    x: number,
    y: number,
    w: number,
    h: number,
    excludeWidgetId?: string
  ): SnapResult {
    if (this.config.type === 'free') {
      return { x, y, w, h, snapped: false }
    }

    const gridPos = this.pixelToGrid(x, y, w, h)

    // 限制在容器范围内
    const maxX = this.config.columns - gridPos.w
    const clampedX = Math.max(0, Math.min(gridPos.x, maxX))
    const clampedY = Math.max(0, gridPos.y)

    // 检查碰撞并调整位置
    const adjusted = this.resolveCollision(
      { x: clampedX, y: clampedY, w: gridPos.w, h: gridPos.h },
      excludeWidgetId
    )

    const pixelPos = this.gridToPixel(adjusted)

    return {
      x: pixelPos.x,
      y: pixelPos.y,
      w: pixelPos.w,
      h: pixelPos.h,
      snapped: true,
    }
  }

  // 检测碰撞
  checkCollision(
    position: GridPosition,
    excludeWidgetId?: string
  ): CollisionResult {
    const collidingWidgets: string[] = []

    for (const [id, widget] of this.widgets) {
      if (id === excludeWidgetId) continue

      const widgetPos = widget.position
      if (
        position.x < widgetPos.x + widgetPos.w &&
        position.x + position.w > widgetPos.x &&
        position.y < widgetPos.y + widgetPos.h &&
        position.y + position.h > widgetPos.y
      ) {
        collidingWidgets.push(id)
      }
    }

    return {
      hasCollision: collidingWidgets.length > 0,
      collidingWidgets,
    }
  }

  // 解决碰撞（简单的向下移动策略）
  private resolveCollision(
    position: GridPosition,
    excludeWidgetId?: string
  ): GridPosition {
    let currentPos = { ...position }
    let maxAttempts = 50

    while (maxAttempts > 0) {
      const collision = this.checkCollision(currentPos, excludeWidgetId)
      if (!collision.hasCollision) {
        return currentPos
      }

      // 向下移动一格
      currentPos.y += 1
      maxAttempts--
    }

    // 如果无法解决碰撞，返回原位置
    return position
  }

  // 调整组件大小
  resizeWidget(
    widgetId: string,
    newW: number,
    newH: number
  ): GridPosition | null {
    const widget = this.widgets.get(widgetId)
    if (!widget) return null

    const newPosition = {
      x: widget.position.x,
      y: widget.position.y,
      w: Math.max(1, Math.min(newW, this.config.columns)),
      h: Math.max(1, newH),
    }

    // 检查并解决碰撞
    const adjusted = this.resolveCollision(newPosition, widgetId)

    return adjusted
  }

  // 移动组件
  moveWidget(
    widgetId: string,
    newX: number,
    newY: number
  ): GridPosition | null {
    const widget = this.widgets.get(widgetId)
    if (!widget) return null

    const newPosition = {
      x: Math.max(0, Math.min(newX, this.config.columns - widget.position.w)),
      y: Math.max(0, newY),
      w: widget.position.w,
      h: widget.position.h,
    }

    // 检查并解决碰撞
    const adjusted = this.resolveCollision(newPosition, widgetId)

    return adjusted
  }

  // 紧凑布局（移除空隙）
  compactLayout(): Map<string, GridPosition> {
    if (this.config.type === 'free') {
      return new Map()
    }

    const sortedWidgets = Array.from(this.widgets.values()).sort(
      (a, b) => {
        if (a.position.y !== b.position.y) {
          return a.position.y - b.position.y
        }
        return a.position.x - b.position.x
      }
    )

    const newPositions = new Map<string, GridPosition>()
    const occupied = new Set<string>()

    for (const widget of sortedWidgets) {
      let newY = 0
      let placed = false

      while (!placed) {
        const testPos = {
          x: widget.position.x,
          y: newY,
          w: widget.position.w,
          h: widget.position.h,
        }

        const posKey = `${testPos.x},${testPos.y}`
        if (!occupied.has(posKey)) {
          // 检查是否与已放置的组件碰撞
          let hasCollision = false
          for (const [, pos] of newPositions) {
            if (
              testPos.x < pos.x + pos.w &&
              testPos.x + testPos.w > pos.x &&
              testPos.y < pos.y + pos.h &&
              testPos.y + testPos.h > pos.y
            ) {
              hasCollision = true
              break
            }
          }

          if (!hasCollision) {
            newPositions.set(widget.id, testPos)
            placed = true
          }
        }

        if (!placed) {
          newY++
        }
      }
    }

    return newPositions
  }

  // 获取对齐辅助线
  getAlignmentGuides(
    widgetId: string,
    threshold: number = 10
  ): Array<{ type: 'horizontal' | 'vertical'; position: number }> {
    const widget = this.widgets.get(widgetId)
    if (!widget) return []

    const guides: Array<{ type: 'horizontal' | 'vertical'; position: number }> =
      []
    const pixelPos = this.gridToPixel(widget.position)

    for (const [id, other] of this.widgets) {
      if (id === widgetId) continue

      const otherPixel = this.gridToPixel(other.position)

      // 水平对齐检查
      const horizontalAlignments = [
        { pos: otherPixel.x, ref: pixelPos.x }, // 左对齐
        { pos: otherPixel.x + otherPixel.w / 2, ref: pixelPos.x + pixelPos.w / 2 }, // 中对齐
        { pos: otherPixel.x + otherPixel.w, ref: pixelPos.x + pixelPos.w }, // 右对齐
      ]

      for (const align of horizontalAlignments) {
        if (Math.abs(align.pos - align.ref) < threshold) {
          guides.push({ type: 'vertical', position: align.pos })
        }
      }

      // 垂直对齐检查
      const verticalAlignments = [
        { pos: otherPixel.y, ref: pixelPos.y }, // 上对齐
        { pos: otherPixel.y + otherPixel.h / 2, ref: pixelPos.y + pixelPos.h / 2 }, // 中对齐
        { pos: otherPixel.y + otherPixel.h, ref: pixelPos.y + pixelPos.h }, // 下对齐
      ]

      for (const align of verticalAlignments) {
        if (Math.abs(align.pos - align.ref) < threshold) {
          guides.push({ type: 'horizontal', position: align.pos })
        }
      }
    }

    return guides
  }

  // 计算布局高度
  calculateLayoutHeight(): number {
    let maxBottom = 0

    for (const widget of this.widgets.values()) {
      const bottom = widget.position.y + widget.position.h
      maxBottom = Math.max(maxBottom, bottom)
    }

    return (
      this.config.padding * 2 +
      maxBottom * (this.config.rowHeight + this.config.gap)
    )
  }

  // 获取空位
  findEmptySpace(
    width: number,
    height: number,
    startY: number = 0
  ): GridPosition | null {
    const maxY = 100 // 最大搜索行数

    for (let y = startY; y < maxY; y++) {
      for (let x = 0; x <= this.config.columns - width; x++) {
        const testPos = { x, y, w: width, h: height }
        const collision = this.checkCollision(testPos)

        if (!collision.hasCollision) {
          return testPos
        }
      }
    }

    return null
  }

  // 添加新组件到最佳位置
  addWidgetAtBestPosition(
    widget: WidgetConfig
  ): GridPosition | null {
    const emptySpace = this.findEmptySpace(
      widget.position.w,
      widget.position.h
    )

    if (emptySpace) {
      return emptySpace
    }

    // 如果没有空位，添加到最底部
    const layoutHeight = this.calculateLayoutHeight()
    const gridY = Math.floor(
      (layoutHeight - this.config.padding) /
      (this.config.rowHeight + this.config.gap)
    )

    return {
      x: 0,
      y: gridY,
      w: widget.position.w,
      h: widget.position.h,
    }
  }

  // 序列化布局
  serializeLayout(): Record<string, GridPosition> {
    const result: Record<string, GridPosition> = {}
    for (const [id, widget] of this.widgets) {
      result[id] = { ...widget.position }
    }
    return result
  }

  // 反序列化布局
  deserializeLayout(layout: Record<string, GridPosition>): void {
    for (const [id, position] of Object.entries(layout)) {
      const widget = this.widgets.get(id)
      if (widget) {
        widget.position = { ...position }
      }
    }
  }
}

export const createLayoutEngine = (
  config?: Partial<LayoutConfig>
): DashboardLayoutEngine => {
  return new DashboardLayoutEngine(config)
}
