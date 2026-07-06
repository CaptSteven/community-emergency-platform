# 社区应急互助与灾害预警平台 · HarmonyOS 端

基于 HarmonyOS（ArkTS / ArkUI，Stage 模型）的单工程双角色应用：登录后依据用户 `role`
在「居民端」与「志愿者端」之间切换。后端为同一套 REST API（见 `common/Api.ets` 中的 `BASE_URL`，
需改成你自己的局域网 IP）。

## 角色与页面

- `pages/LoginPage` 登录（登录成功后异步上报推送 Token）
- `pages/ResidentHomePage` 居民端：查看预警、提交求助、附近避难所、站内消息
- `pages/SubmitHelpPage` 居民提交求助（含定位）
- `pages/VolunteerHomePage` 志愿者端：接单、完成任务、查看位置/导航
- `pages/NearbyShelterPage` 附近避难所（地图 + 列表）
- `pages/NotificationsPage` 站内消息

## HarmonyOS Kit 使用一览

| 能力 | 使用的 Kit | 代码位置 | 说明 |
| --- | --- | --- | --- |
| 定位（核心） | Location Kit（`@ohos.geoLocationManager` + `@ohos.abilityAccessCtrl`） | `common/LocationService.ets` | 运行时申请 `LOCATION` / `APPROXIMATELY_LOCATION` 权限并获取当前经纬度，返回 `LocationResult`，失败抛出中文 `Error`。 |
| 提交求助带定位 | Location Kit | `pages/SubmitHelpPage.ets` | 「获取当前定位」按钮，经纬度以字符串写入 `SubmitHelpPayload.latitude/longitude`（可选，缺省允许提交）。 |
| 附近避难所地图 | Map Kit（`@kit.MapKit`） | `pages/NearbyShelterPage.ets` | 通过 `GET /shelters/nearby/` 拉取避难所；尝试用 `MapComponent` 渲染地图并打点，未配置 AGC 时经 `mapReady` 标志与 try/catch 自动降级为富文本列表（名称/距离/地址/容量/联系电话/导航）。 |
| 志愿者导航 | Map Kit / 列表降级 | `pages/VolunteerHomePage.ets` → `NearbyShelterPage` | 每条带地址的任务提供「查看位置/导航」，携带求助标题与地址跳转避难所/导航页。 |
| 消息推送注册 | Push Kit（`@kit.PushKit`） | `common/PushService.ets` | 登录成功后 fire-and-forget 获取设备 Token 并 `POST /auth/device-token/`；全程 try/catch，未配置时静默降级，绝不阻塞登录。 |
| 服务卡片 | Form Kit（`@kit.FormKit`） | `entryformability/EntryFormAbility.ets`、`widget/pages/WarningCard.ets`、`resources/base/profile/form_config.json` | 2x2 卡片展示应急预警提示，`postCardAction(message)` 触发 `onFormEvent` 刷新。 |

## 权限

`module.json5` 已声明：

- `ohos.permission.INTERNET`
- `ohos.permission.LOCATION`（reason：`$string:location_reason`）
- `ohos.permission.APPROXIMATELY_LOCATION`（reason：`$string:approximately_location_reason`）

## 后端接口契约（与后端约定）

- `POST /help-requests/`：新增可选 `latitude` / `longitude`（十进制字符串）。
- `POST /auth/device-token/`：`{ "push_token": string, "platform": "harmony" }`，需鉴权。
- `GET /shelters/nearby/?lat=<>&lng=<>&limit=10`：返回带 `distance_km` 的避难所数组。

## 需要评审者补齐真实配置的位置（AppGallery Connect）

> 以下 HMS 能力在纯净构建中可能无法解析或运行为空，均已用 try/catch 降级，不影响 Location Kit + REST 的核心链路。

1. **Map Kit**：需在 AppGallery Connect 开通地图服务并下载 `agconnect-services.json`（放入 `AppScope`）、
   在 `oh-package.json5` / 签名中配置 API Key，`NearbyShelterPage` 的 `MapComponent` 方可真实渲染，
   否则自动使用列表。
2. **Push Kit**：需开通推送服务并完成 AGC 配置，`PushService.getToken()` 才能返回真实 Token；
   未配置时上报被静默跳过。
3. **`common/Api.ets` `BASE_URL`**：改为后端实际可达地址。
4. **服务卡片数据源**：`EntryFormAbility.onUpdateForm` 当前为默认文案，可接入后端预警/待处理求助接口填充真实数据。
