import geoLocationManager from '@ohos.geoLocationManager'
import abilityAccessCtrl from '@ohos.abilityAccessCtrl'
import { Permissions } from '@ohos.abilityAccessCtrl'
import common from '@ohos.app.ability.common'
import { LocationResult } from '../model/Models'

// Location Kit 封装：运行时申请定位权限并获取当前经纬度。
// 失败时抛出带中文说明的 Error，调用方可直接 toast。
export class LocationService {
  private static readonly PERMISSIONS: Array<Permissions> = [
    'ohos.permission.LOCATION',
    'ohos.permission.APPROXIMATELY_LOCATION'
  ]

  // 运行时申请定位权限，返回是否全部授权
  private static async requestPermissions(): Promise<boolean> {
    let context = getContext() as common.UIAbilityContext
    let atManager: abilityAccessCtrl.AtManager = abilityAccessCtrl.createAtManager()

    let result = await atManager.requestPermissionsFromUser(context, LocationService.PERMISSIONS)
    let grantStatus: Array<number> = result.authResults

    for (let i = 0; i < grantStatus.length; i++) {
      if (grantStatus[i] !== 0) {
        return false
      }
    }
    return true
  }

  // 获取当前定位。未授权或获取失败时抛出中文 Error。
  static async getCurrentLocation(): Promise<LocationResult> {
    let granted = await LocationService.requestPermissions()
    if (!granted) {
      throw new Error('未授予定位权限，请在系统设置中开启')
    }

    let requestInfo: geoLocationManager.CurrentLocationRequest = {
      priority: geoLocationManager.LocationRequestPriority.FIRST_FIX,
      scenario: geoLocationManager.LocationRequestScenario.UNSET,
      maxAccuracy: 0,
      timeoutMs: 10000
    }

    try {
      let location: geoLocationManager.Location =
        await geoLocationManager.getCurrentLocation(requestInfo)
      let result: LocationResult = {
        latitude: location.latitude,
        longitude: location.longitude
      }
      return result
    } catch (err) {
      throw new Error('获取定位失败，请确认已开启定位服务')
    }
  }
}
