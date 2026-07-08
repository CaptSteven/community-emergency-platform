import http from '@ohos.net.http'
import fs from '@ohos.file.fs'
import util from '@ohos.util'
import router from '@ohos.router'
import { preferences } from '@kit.ArkData'
import { common } from '@kit.AbilityKit'
import { EmptyPayload, PaginatedList, UserInfo } from '../model/Models'

// base64 图片上传载荷（uploadFile 专用）
interface UploadB64Payload {
  photo_b64: string
  field: string
}

export class Session {
  static token: string = ''
  static userId: number = 0
  static username: string = ''
  static role: string = ''
  static phone: string = ''
  static community: string = ''
  static address: string = ''
  static skills: string = ''

  static saveUser(user: UserInfo): void {
    Session.userId = user.id
    Session.username = user.username
    Session.role = user.role
    Session.phone = user.phone || ''
    Session.community = user.community || ''
    Session.address = user.address || ''
    Session.skills = user.skills || ''
  }

  static async persist(context: common.UIAbilityContext): Promise<void> {
    let store = await preferences.getPreferences(context, { name: 'session' } as preferences.Options)
    await store.put('token', Session.token)
    await store.put('userId', Session.userId)
    await store.put('username', Session.username)
    await store.put('role', Session.role)
    await store.put('phone', Session.phone)
    await store.put('community', Session.community)
    await store.put('address', Session.address)
    await store.put('skills', Session.skills)
    await store.flush()
  }

  static async restore(context: common.UIAbilityContext): Promise<boolean> {
    let store = await preferences.getPreferences(context, { name: 'session' } as preferences.Options)
    let token = await store.get('token', '') as string
    if (token === '') {
      return false
    }
    Session.token = token
    Session.userId = await store.get('userId', 0) as number
    Session.username = await store.get('username', '') as string
    Session.role = await store.get('role', '') as string
    Session.phone = await store.get('phone', '') as string
    Session.community = await store.get('community', '') as string
    Session.address = await store.get('address', '') as string
    Session.skills = await store.get('skills', '') as string
    return true
  }

  static async clear(context: common.UIAbilityContext): Promise<void> {
    Session.token = ''
    Session.userId = 0
    Session.username = ''
    Session.role = ''
    Session.phone = ''
    Session.community = ''
    Session.address = ''
    Session.skills = ''
    let store = await preferences.getPreferences(context, { name: 'session' } as preferences.Options)
    await store.clear()
    await store.flush()
  }
}

export class Api {
  static BASE_URL: string = 'http://10.204.190.31:8000/api'

  static async get(path: string): Promise<Object> {
    return await Api.request<EmptyPayload>(path, http.RequestMethod.GET)
  }

  static async getList<T>(path: string): Promise<T[]> {
    let response = await Api.request<EmptyPayload>(path, http.RequestMethod.GET)
    if (Array.isArray(response)) {
      return response as T[]
    }
    let paginated = response as PaginatedList<T>
    return paginated.results || []
  }

  static async getPaginated<T>(path: string): Promise<PaginatedList<T>> {
    let response = await Api.request<EmptyPayload>(path, http.RequestMethod.GET)
    return response as PaginatedList<T>
  }

  static async post<T>(path: string, data: T): Promise<Object> {
    return await Api.request<T>(path, http.RequestMethod.POST, data)
  }

  static async postEmpty(path: string): Promise<Object> {
    return await Api.request<EmptyPayload>(path, http.RequestMethod.POST)
  }

  static async put<T>(path: string, data: T): Promise<Object> {
    return await Api.request<T>(path, http.RequestMethod.PUT, data)
  }

  // 上传本地图片：读文件 → base64 → JSON POST {photo_b64, field}。
  // 后端各上传接口兼容 multipart 与 base64 双通道；App 走 base64，
  // 因为鸿蒙 http 模块的 multipart（filePath/data 部件）在部分设备与模拟器上会发出空文件。
  static async uploadFile(path: string, filePath: string, fieldName: string): Promise<Object> {
    let stat = fs.statSync(filePath)
    let buf = new ArrayBuffer(stat.size)
    let file = fs.openSync(filePath, fs.OpenMode.READ_ONLY)
    fs.readSync(file.fd, buf)
    fs.closeSync(file)
    let b64: string = new util.Base64Helper().encodeToStringSync(new Uint8Array(buf))
    let payload: UploadB64Payload = { photo_b64: b64, field: fieldName }
    return await Api.request<UploadB64Payload>(path, http.RequestMethod.POST, payload)
  }

  static async request<T>(
    path: string,
    method: http.RequestMethod,
    data?: T
  ): Promise<Object> {
    let httpRequest = http.createHttp()

    let headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }

    if (Session.token !== '') {
      headers['Authorization'] = `Token ${Session.token}`
    }

    let options: http.HttpRequestOptions = {
      method: method,
      header: headers,
      expectDataType: http.HttpDataType.STRING,
      connectTimeout: 10000,
      readTimeout: 10000
    }

    if (data !== undefined) {
      options.extraData = JSON.stringify(data)
    }

    try {
      let response = await httpRequest.request(Api.BASE_URL + path, options)

      let statusCode = response.responseCode
      let resultText = response.result as string

      if (statusCode === 401) {
        Session.token = ''
        Session.userId = 0
        Session.username = ''
        Session.role = ''
        router.replaceUrl({ url: 'pages/LoginPage' })
        throw new Error('登录已失效，请重新登录')
      }

      if (statusCode === 403) {
        throw new Error('无权限访问该功能')
      }

      if (statusCode < 200 || statusCode >= 300) {
        let errorMessage = resultText
        try {
          let errorData = JSON.parse(resultText) as Record<string, Object>
          if (errorData['message']) {
            errorMessage = errorData['message'] as string
          } else if (errorData['detail']) {
            errorMessage = errorData['detail'] as string
          }
        } catch (parseError) {
          // resultText 不是 JSON 时直接使用原始内容。
        }
        throw new Error(errorMessage)
      }

      if (resultText === '' || resultText === undefined || resultText === null) {
        let empty: EmptyPayload = {}
        return empty
      }

      return JSON.parse(resultText) as Object
    } finally {
      httpRequest.destroy()
    }
  }
}