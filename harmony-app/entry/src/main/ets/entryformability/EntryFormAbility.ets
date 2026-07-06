import { FormExtensionAbility, formBindingData, formProvider } from '@kit.FormKit'
import { Want } from '@kit.AbilityKit'
import { hilog } from '@kit.PerformanceAnalysisKit'

const DOMAIN = 0x0000

// 卡片数据形状，供 formBindingData 使用
interface WarningCardData {
  title: string
  subtitle: string
}

// 服务卡片（Form Kit）：展示最新灾害预警 / 待处理求助提示。
// 说明：真实数据可在 onUpdateForm 中通过后端接口拉取；此处提供稳健的默认文案，
// 未接入数据源时卡片仍可正常显示与刷新。
export default class EntryFormAbility extends FormExtensionAbility {
  private buildData(subtitle: string): formBindingData.FormBindingData {
    let data: WarningCardData = {
      title: '社区应急预警',
      subtitle: subtitle
    }
    return formBindingData.createFormBindingData(data)
  }

  onAddForm(want: Want): formBindingData.FormBindingData {
    hilog.info(DOMAIN, 'testTag', 'form onAddForm')
    return this.buildData('打开应用查看最新预警与待处理求助')
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
