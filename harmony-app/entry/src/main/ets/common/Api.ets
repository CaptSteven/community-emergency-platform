import http from '@ohos.net.http'
import { EmptyPayload } from '../model/Models'

export class Session {
  static token: string = ''
  static userId: number = 0
  static username: string = ''
  static role: string = ''
}

export class Api {
  // 注意：这里改成你自己电脑的局域网 IP
  static BASE_URL: string = 'http://10.110.56.10:8000/api'

  static async get(path: string): Promise<Object> {
    return await Api.request<EmptyPayload>(path, http.RequestMethod.GET)
  }

  static async post<T>(path: string, data: T): Promise<Object> {
    return await Api.request<T>(path, http.RequestMethod.POST, data)
  }

  static async postEmpty(path: string): Promise<Object> {
    return await Api.request<EmptyPayload>(path, http.RequestMethod.POST)
  }

  // HarmonyOS 这里没有 PATCH，先用 PUT 代替
  static async put<T>(path: string, data: T): Promise<Object> {
    return await Api.request<T>(path, http.RequestMethod.PUT, data)
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

      if (statusCode < 200 || statusCode >= 300) {
        throw new Error(resultText)
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