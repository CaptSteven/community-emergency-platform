import { Api } from './Api'
import { DeviceTokenPayload } from '../model/Models'
// Push Kit 需在 AppGallery Connect 配置后生效，未配置时该导入在构建阶段可能无法解析，
// 属预期情况；运行期所有调用均以 try/catch 包裹，绝不阻塞登录流程。
import { pushService } from '@kit.PushKit'

// Push Kit 封装：获取设备推送 Token 并上报后端 /auth/device-token/。
export class PushService {
  // 登录成功后 fire-and-forget 调用。任何异常都会被静默吞掉。
  static async registerToken(): Promise<void> {
    try {
      let token: string = await pushService.getToken()

      if (!token || token === '') {
        return
      }

      let payload: DeviceTokenPayload = {
        push_token: token,
        platform: 'harmony'
      }
      await Api.post<DeviceTokenPayload>('/auth/device-token/', payload)
    } catch (err) {
      // Push Kit 未配置或上报失败：静默降级，不影响登录。
      console.info('PushService 上报设备令牌失败（可忽略）: ' + JSON.stringify(err))
    }
  }
}
