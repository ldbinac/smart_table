import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import MemberSelect from '../MemberSelect.vue'
import { userApi } from '@/api/user'

// Mock API
vi.mock('@/api/user', () => ({
  userApi: {
    searchUsers: vi.fn(),
    getUserById: vi.fn(),
  },
}))

describe('MemberSelect', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('基础渲染', () => {
    it('应该正确渲染占位符', () => {
      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: null,
          placeholder: '请选择成员',
        },
      })

      expect(wrapper.find('.placeholder').text()).toBe('请选择成员')
    })

    it('应该正确渲染已选成员', async () => {
      const mockUser = {
        id: '1',
        name: '张三',
        email: 'zhangsan@example.com',
        avatar: null,
      }

      vi.mocked(userApi.getUserById).mockResolvedValue(mockUser)

      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: '1',
        },
      })

      await flushPromises()

      expect(wrapper.find('.member-name').text()).toBe('张三')
    })
  })

  describe('搜索功能', () => {
    it('空查询时不应该调用搜索接口', async () => {
      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: null,
        },
      })

      // 打开下拉框
      await wrapper.find('.member-select-trigger').trigger('click')
      await nextTick()

      // 等待防抖时间
      await new Promise(resolve => setTimeout(resolve, 350))

      expect(userApi.searchUsers).not.toHaveBeenCalled()
    })

    it('输入关键词后应该调用搜索接口', async () => {
      const mockResponse = {
        users: [
          { id: '1', name: '张三', email: 'zhangsan@example.com', avatar: null },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
      }

      vi.mocked(userApi.searchUsers).mockResolvedValue(mockResponse)

      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: null,
        },
      })

      // 打开下拉框
      await wrapper.find('.member-select-trigger').trigger('click')
      await nextTick()

      // 输入搜索关键词
      const input = wrapper.find('.el-input__inner')
      await input.setValue('张三')

      // 等待防抖时间
      await new Promise(resolve => setTimeout(resolve, 350))

      expect(userApi.searchUsers).toHaveBeenCalledWith({
        query: '张三',
        base_id: undefined,
        per_page: 20,
      })
    })

    it('搜索失败时应该显示错误提示', async () => {
      vi.mocked(userApi.searchUsers).mockRejectedValue(new Error('网络错误'))

      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: null,
        },
      })

      // 打开下拉框
      await wrapper.find('.member-select-trigger').trigger('click')
      await nextTick()

      // 输入搜索关键词
      const input = wrapper.find('.el-input__inner')
      await input.setValue('张三')

      // 等待防抖时间
      await new Promise(resolve => setTimeout(resolve, 350))

      await flushPromises()

      // 应该显示空结果
      expect(wrapper.find('.empty-state').exists()).toBe(true)
    })
  })

  describe('选择功能', () => {
    it('单选模式下选择成员应该更新 modelValue', async () => {
      const mockResponse = {
        users: [
          { id: '1', name: '张三', email: 'zhangsan@example.com', avatar: null },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
      }

      vi.mocked(userApi.searchUsers).mockResolvedValue(mockResponse)

      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: null,
          'onUpdate:modelValue': vi.fn(),
        },
      })

      // 打开下拉框并搜索
      await wrapper.find('.member-select-trigger').trigger('click')
      await nextTick()

      const input = wrapper.find('.el-input__inner')
      await input.setValue('张')
      await new Promise(resolve => setTimeout(resolve, 350))
      await flushPromises()

      // 点击选择成员
      await wrapper.find('.member-option').trigger('click')

      // 验证事件被触发
      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')![0]).toEqual(['1'])
    })

    it('应该正确移除已选成员', async () => {
      const mockUser = {
        id: '1',
        name: '张三',
        email: 'zhangsan@example.com',
        avatar: null,
      }

      vi.mocked(userApi.getUserById).mockResolvedValue(mockUser)

      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: '1',
          'onUpdate:modelValue': vi.fn(),
        },
      })

      await flushPromises()

      // 点击移除按钮
      await wrapper.find('.remove-icon').trigger('click')

      // 验证事件被触发
      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')![0]).toEqual([null])
    })
  })

  describe('禁用状态', () => {
    it('禁用状态下不应该响应点击事件', async () => {
      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: null,
          disabled: true,
        },
      })

      const trigger = wrapper.find('.member-select-trigger')
      expect(trigger.classes()).toContain('is-disabled')
    })

    it('禁用状态下不应该显示移除按钮', async () => {
      const mockUser = {
        id: '1',
        name: '张三',
        email: 'zhangsan@example.com',
        avatar: null,
      }

      vi.mocked(userApi.getUserById).mockResolvedValue(mockUser)

      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: '1',
          disabled: true,
        },
      })

      await flushPromises()

      expect(wrapper.find('.remove-icon').exists()).toBe(false)
    })
  })

  describe('多选模式', () => {
    it('多选模式下应该允许多个选择', async () => {
      const mockResponse = {
        users: [
          { id: '1', name: '张三', email: 'zhangsan@example.com', avatar: null },
          { id: '2', name: '李四', email: 'lisi@example.com', avatar: null },
        ],
        total: 2,
        page: 1,
        per_page: 20,
        total_pages: 1,
      }

      vi.mocked(userApi.searchUsers).mockResolvedValue(mockResponse)

      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: [],
          allowMultiple: true,
          'onUpdate:modelValue': vi.fn(),
        },
      })

      // 打开下拉框并搜索
      await wrapper.find('.member-select-trigger').trigger('click')
      await nextTick()

      const input = wrapper.find('.el-input__inner')
      await input.setValue('张')
      await new Promise(resolve => setTimeout(resolve, 350))
      await flushPromises()

      // 选择第一个成员
      const options = wrapper.findAll('.member-option')
      await options[0].trigger('click')

      // 验证事件被触发且值为数组
      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')![0]).toEqual([['1']])
    })

    it('多选模式下应该显示清空按钮', async () => {
      const mockUser = {
        id: '1',
        name: '张三',
        email: 'zhangsan@example.com',
        avatar: null,
      }

      vi.mocked(userApi.getUserById).mockResolvedValue(mockUser)

      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: ['1'],
          allowMultiple: true,
        },
      })

      await flushPromises()

      expect(wrapper.find('.clear-all-icon').exists()).toBe(true)
    })
  })

  describe('空状态显示', () => {
    it('未输入关键词时应该显示提示', async () => {
      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: null,
        },
      })

      // 打开下拉框
      await wrapper.find('.member-select-trigger').trigger('click')
      await nextTick()

      // 等待初始化
      await new Promise(resolve => setTimeout(resolve, 100))

      const emptyState = wrapper.find('.empty-state')
      expect(emptyState.exists()).toBe(true)
      expect(emptyState.text()).toContain('请输入关键词搜索')
    })

    it('搜索无结果时应该显示提示', async () => {
      const mockResponse = {
        users: [],
        total: 0,
        page: 1,
        per_page: 20,
        total_pages: 0,
      }

      vi.mocked(userApi.searchUsers).mockResolvedValue(mockResponse)

      const wrapper = mount(MemberSelect, {
        props: {
          modelValue: null,
        },
      })

      // 打开下拉框并搜索
      await wrapper.find('.member-select-trigger').trigger('click')
      await nextTick()

      const input = wrapper.find('.el-input__inner')
      await input.setValue('不存在的用户')
      await new Promise(resolve => setTimeout(resolve, 350))
      await flushPromises()

      const emptyState = wrapper.find('.empty-state')
      expect(emptyState.exists()).toBe(true)
      expect(emptyState.text()).toContain('未找到匹配的成员')
    })
  })
})
