import { FormExtensionAbility, formBindingData, formProvider } from '@kit.FormKit'
import { Want } from '@kit.AbilityKit'
import { hilog } from '@kit.PerformanceAnalysisKit'

const DOMAIN = 0x0000

// 卡片数据形状，供 formBindingData 使用
interface WarningCardData {
  title: string
  subtitle: string
}

// 服务卡片（Form Kit）：纯社区服务入口，不展示任何灾害预警内容。
// 说明：此处提供稳健的静态文案，未接入数据源时卡片仍可正常显示与刷新。
export default class EntryFormAbility extends FormExtensionAbility {
  private buildData(subtitle: string): formBindingData.FormBindingData {
    let data: WarningCardData = {
      title: '社区服务',
      subtitle: subtitle
    }
    return formBindingData.createFormBindingData(data)
  }

  onAddForm(want: Want): formBindingData.FormBindingData {
    hilog.info(DOMAIN, 'testTag', 'form onAddForm')
    return this.buildData('打开应用查看社区上门服务')
  }

  onUpdateForm(formId: string): void {
    hilog.info(DOMAIN, 'testTag', 'form onUpdateForm')
    let data = this.buildData('已刷新 · 点击卡片查看详情')
    formProvider.updateForm(formId, data).catch((err: Object) => {
      hilog.error(DOMAIN, 'testTag', 'updateForm failed: %{public}s', JSON.stringify(err))
    })
  }

  // 卡片内 postCardAction(message) 触发，用于刷新
  onFormEvent(formId: string, message: string): void {
    hilog.info(DOMAIN, 'testTag', 'form onFormEvent %{public}s', message)
    this.onUpdateForm(formId)
  }

  onRemoveForm(formId: string): void {
    hilog.info(DOMAIN, 'testTag', 'form onRemoveForm %{public}s', formId)
  }
}
