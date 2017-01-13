FORMAT: 1A
HOST: https://g.sportscool.cn/api/2

# 派队管家接口

# Group 使用指南

### 设计规范

1. 使用标准 RESTful 模式
2. 请求和返回数据类型统一为 JSON
3. 错误返回使用 http status code，并且在 body 中包含JSON格式的错误说明
4. 列表的key需使用对应类型的复数形式如 users teams，不能使用不相关名称如: results data


# Group 接口签名

### 权限分配

对于每个类型客户端服务端会分配 apiKey 和 apiSecret 做安全签名使用

### 系统级Header
```http
Accept: application/json
X-Api-Key: jGw7SRN6qckRc0jz //请求apiKey，由后端分发
X-Signature: 8STR59mJWFKv11GhdzSwd9iBzsySRKjt //根据签名算法算出的签名
X-Access-Token: 5262d64b892e8d4341000001 // 用户登录后的AccessToken(
X-App-Version: 2.0
X-Timestamp: 1456905123049 // 时间戳，为时间转换为的毫秒
X-Nonce: MBESwVRPSBgf48npjfuMPFzCGwMjLIac // 32位随机字符串，防重放
```

### 签名算法

#### 第一步：组织参与签名计算的字符串

string_to_sign = HTTPMethod+Path+Args+json_body_base64+Timestamp+Nonce

1. HTTPMethod 为请求方法的大写，如 GET POST  
2. Path 为请求接口地址 path ，比如请求地址为 https://g.sportscool.cn/api/1/users 的 path 为 /api/1/users
3. Args 为将所有请求参数（包括 query 和 body 中的参数）以 key=value组合，然后按字母顺序排列后使用 & 符号连接在一起，注意当提交类型为 Form 时，file 类型参数不参与签名
4. json_body_base64 如果请求 body 为 json 时此值为 body 内容使用 base64 编码后的值，body 非 json 时此值为空 
5. Timestamp 和 Nonce 分别与头部中 X-Timestamp 和 X-Nonce 值相同
6. 所有参数和 json_body 在计算时需要移除首尾空白字符，包括空格和回车等，但在请求时可以包含首尾空白符仅不参与签名

#### 第二步：使用分配的 apiSecret 和 hmac-sha256 算法生成签名

算法参考：
http://www.jokecamp.com/blog/examples-of-creating-base64-hashes-using-hmac-sha256-in-different-languages/

先使用 hmac-sha256 对第一步得到的 string_to_sign 做 hash 运算并将得到的值使用 base64 编码

```java
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.apache.commons.codec.binary.Base64;

public class GenerateSignature {
  public static void main(String[] args) {
    try {
     String apiSecret = "secret";
     String stringToSign = "string_to_sign";

     Mac sha256_HMAC = Mac.getInstance("HmacSHA256");
     SecretKeySpec secret_key = new SecretKeySpec(apiSecret.getBytes(), "HmacSHA256");
     sha256_HMAC.init(secret_key);

     String hash = Base64.encodeBase64String(sha256_HMAC.doFinal(stringToSign.getBytes()));
     System.out.println(hash);
    }
    catch (Exception e){
     System.out.println("Error");
    }
   }
}
```

#### 第三步：将生成的签名字符串以 X-Signature 为 key 放入请求头部

# Group 版本

### 版本

0.3(draft)

### 更新记录

无

# Data Structures

## Sport(object)
+ id: 1(number)
+ name: 羽毛球

## Photo(object)
+ url: `http://icon.qiniucdn.com/1.jpg`
+ sizes(array)
    + `!c256`
    + `!c512`
    + `!c1024`

## Team(object)
+ id: 20 (number, required)
+ name: Team Name (string)
+ icon(Photo) - 微标
+ owner(User)
+ description: ` ` (string) - 俱乐部介绍
+ contact_person: 张三 (string) - 联系人
+ contact_phone: 13838003800 (string) - 联系电话
+ open_type: 0 (number) - 开放类型： 0 允许任何人加入， 1 需要验证， 2 交会费加入， 3 不允许任何人加入

## TeamSample(object)
+ id: 20 (number, required)
+ name: Team Name (string) - 俱乐部或赛事主办名称
+ icon(Photo) - 微标

## TeamMemberGroup(object)
+ name: Group Name (string)

## Activity(object)
+ id: 20 (number, required)
+ title: Activity Name (string)
+ team(Team)
+ creator(User)
+ type: 0 (number) - 活动类型: 0 活动 1 比赛
+ sport(Sport) - 运动类型
+ leader(User) - 组织者
+ contact_person: 张三 (string) - 联系人
+ contact_phone: 13838003800 (string) - 联系电话
+ description: ` ` (string) - 活动描述，html格式
+ country: 中国 (string)
+ province: 四川 (string)
+ city: 成都 (string)
+ address: 天府软件园D区5栋羽毛球场 (string) - 活动地址
+ lat: 90.1 (number)
+ lng: 104.55 (number)
+ gym_id: 1 (number) - 场馆ID
+ min_members: 0 (number) - 活动最少人数，如果报名数未达到此人数则自动取消（由于俱乐部会在不同途径发布活动此设置基本无效）
+ max_members: 20 (number) - 每人数限制, 报名满后无法继续报名
+ public_memebers: true (boolean) - 是否公开报名列表
+ members_count: 100 (number) - 活动报名总人数
+ comments_count: 20 (number) - 评论数
+ recommend_time: 1458530332 (number) - 推荐时间，被推荐的时间戳，推荐活动列表
+ recommend_region: 0 (number) - 推荐范围： 0 全国 1 同城
+ payment_type: 0 (number) - 支付方式： 0 在线支付 1 线下支付, 不能修改
+ allow_free_times: true (boolean) - 允许使用次卡
+ allow_groups(array) - 分组限制，为空则表示无限制
    + 高级组 (string)
+ allow_agents: 0 (number) - 允许代报人数，注意代报人数并不包含报名人自己，因此如果允许代报人数为0则表示不允许代报，只能自己报名
+ start_time: `2016-03-18 18:00:00` (string) - 开始时间
+ end_time: `2016-04-18 18:00:00` (string) - 结束时间
+ join_start: `2016-02-18 18:00:00` (string) - 报名开始时间
+ join_end: `2016-03-05 18:00:00` (string)- 报名截止时间
+ cancelled: `2016-03-18 18:00:00` (string) - 取消时间
+ cancel_reason: ` ` (string) 取消原因
+ verified: false (boolean) - 是否已认证
+ verify_reason: ` ` (string) - 认证原因
+ price: 20.00 (number) - 价格
+ female_price: 15.00 (number) - 女生价格
+ vip_price: 15.00 (number) - VIP价格
+ join_level_discount: false (boolean) - 是否参加会员折扣
+ need_nickname: false (boolean) - 报名需要昵称
+ need_mobile: false (boolean) - 报名需要填写手机
+ need_gender: false (boolean) - 报名需要填写性别
+ need_name: false (boolean) - 报名需要填写姓名
+ need_identification: false (boolean) - 报名需要填写身份证
+ need_emergency_contact: false (boolean) - 报名需要紧急联系人
+ need_gps: false (boolean) - 是否实时地理位置，如果需要实时地理位置需要提醒用户活动期间会自动上传实时位置信息
+ need_ext1_name: `期望名牌号` (string) - 扩展属性1名称，如果扩展属性名称为空则表示不需要此扩展属性
+ need_ext1_type: text (string) - 扩展属性1类型： text 文本，photo 照片，根据扩展属性类型在报名表中显示对应的输入框供用户提供对应资料
+ need_ext2_name: ` ` (string) - 扩展属性2名称
+ need_ext2_type: text (string) - 扩展属性2类型 text 文本，photo 照片
+ need_ext3_name: ` ` (string) - 扩展属性3名称
+ need_ext3_type: text (string) - 扩展属性3类型 text 文本，photo 照片
+ visible: 0 (number) -  可见性: 0 所有人 1 仅成员，如果可见性为1则表示需要加入俱乐部才可以看到和报名
+ refund_type: 1 (number) -  退款策略：0 随时退款，1 报名截止前可退，2 不能退款
+ created: `2016-03-18 18:00:00` (string) - 创建时间
+ updated: `2016-03-18 18:00:00` (string) - 最后更新时间
+ state: 1 (number) - 活动状态：0 已关闭 1 上架中 2 已结束

## User(object)
+ name: Boba Fett
+ signature: `今晚打老虎` - 个性签名
+ mobile: 13838003800
+ avatar(object)
    + url: `http://avatar.qiniucdn.com/1.jpg`
    + sizes(array)
        + `!c256`
        + `!c512`
        + `!c1024`
+ gender: m (string) - 性别：f 女， m 男
+ dob: `1990-01-01` (string) - 生日
+ created: `2016-03-18 18:00:00` (string) - 注册时间

## AccountLog(object)
+ change_type: activity (string)
+ credit_change: 100.00 (number)

## Order(object)
+ order_type: 0 (number) - 订单类型
+ order_no: 2016070410021 (number) - 订单号
+ team(Team) - 所属俱乐部
+ user(User) - 下单用户
+ order_type: 0 (number) - 订单类型：0 活动 1 消费 2 赛事
+ activity_id: 0 (number) - 活动ID
+ title: 活动1 (string) - 订单标题
+ note: ` ` (string) - 订单备注
+ total_fee: 10.5 (number) - 订单总金额
+ credit_fee: 0.0 (number) - 余额抵扣
+ discount_fee: 0.0 (number) - 优惠金额
+ discount_code: ` ` (string) - 折扣码
+ discount_reason: ` ` (string) - 优惠原因
+ use_integral: 0 (string) - 使用积分数量
+ integral_fee: 0.0 (number) - 积分抵扣金额
+ payment_fee: 0.0 (number) - 实付金额 = 订单总金额 - 余额抵扣 - 优惠金额
+ payment_method: wxpay (string) - 支付方法 wxpay alipay
+ gateway_trade_no: 4007522001201603184088746125 (string) - 支付平台订单号
+ gateway_account: name@example.com (string) - 支付平台账号
+ refund_state: NO_REFUND (string) - 退款状态：NO_REFUND（无退款）PARTIAL_REFUNDING（部分退款中）PARTIAL_REFUNDED（已部分退款） PARTIAL_REFUND_FAILED（部分退款失败）FULL_REFUNDING（全额退款中）FULL_REFUNDED（已全额退款）FULL_REFUND_FAILED（全额退款失败）
+ refunded_fee: 0.0 (number) - 退款金额（允许部分退款）
+ refunded_time: `2016-03-18 18:00:00` (string) - 退款时间
+ state: WAIT_BUYER_PAY (string) - 订单状态: WAIT_BUYER_PAY(待支付) WAIT_PAY_RETURN（等待支付确认）TRADE_PAID（已支付）TRADE_FINISHED（交易结束） TRADE_CLOSED（付款以后用户退款成功，交易自动关闭）TRADE_CLOSED_BY_USER（付款以前，卖家或买家主动关闭交易）
+ paid: `2016-03-18 18:00:00` (string) - 支付完成时间
+ finished: `2016-03-18 18:00:00`  (string) - 完成时间
+ created: `2016-03-18 18:00:00`  (string) - 下单时间
+ updated: `2016-03-18 18:00:00`  (string) - 最后更新时间
+ cancelled: `2016-03-18 18:00:00`  (string) - 取消时间
+ cancel_reason: `2016-03-18 18:00:00`  (string) - 取消原因

## MatchCover(object)
+ position: home (string) - 显示位置： home 赛事首页, description 赛事简介页面, statuses 战报页面, rules 规程页面, rounds 赛程页面
+ url: `http://avatar.qiniucdn.com/1.jpg`
+ sizes(array)
    + `!c256`
    + `!c512`
    + `!c1024`

## MatchGroup(object)
+ name: Test Group (string) - 分组名称
+ price: 100.99 (number) - 报名费
+ max_members: 1000 (number) - 参赛者数量限制
+ members_count: 10 (number) - 已报数量

## Match(object)
+ id: 20 (number, required)
+ title: Match title (string)
+ team_id: 1 (number) - 赛事主办方ID
+ team(TeamSample) - 赛事主办信息
+ user_id: 1000 (number) - 创建人ID
+ type: 0 (number) - 类型: 0 对战型，如：足球、蓝球，1 非对战型，如：跑步、自行车
+ sports(array[number]) - 运动类型
+ contact: 张三 (string) - 联系方式
+ description: 赛事描述 (string) - 赛事描述
+ rules: 赛事规程 (string) - 赛事规程(html格式字符串)
+ reward: 第一名1000块 (string) - 奖励说明
+ country: 中国 (string)
+ province: 四川 (string)
+ city: 成都 (string)
+ address: 天府软件园D区5栋羽毛球场 (string) - 赛事地址（注：由于赛事轮次可以单独设置地址，此地址可能是报名或总赛地址）
+ lat: 90.1 (number)
+ lng: 104.55 (number)
+ members_count: 100 (number) - 赛事报名总人数或团队数
+ comments_count: 20 (number) - 评论数
+ recommend_time: 1458530332 (number) - 推荐时间，被推荐的时间戳，推荐活动列表
+ recommend_region: 0 (number) - 推荐范围： 0 全国 1 同城
+ join_type: 0 (number) - 报名类型： 0 个人 1 团队
+ payment_type: 0 (number) - 支付方式： 0 线上支付 1 线下支付 2 均可
+ start_time: `2016-03-18 18:00:00` (string) - 开始时间 
+ end_time: `2016-04-18 18:00:00` (string) - 结束时间
+ join_start: `2016-02-18 18:00:00` (string) - 报名开始时间，为空则表示通过审核后即可报名
+ join_end: `2016-03-05 18:00:00` (string)- 报名截止时间，为空则开始前均可报名
+ cancelled: `2016-03-18 18:00:00` (string) - 取消时间
+ cancel_reason: ` ` (string) 取消原因
+ verified: false (boolean) - 是否已认证
+ verify_reason: ` ` (string) - 认证原因
+ price: 20.00 (number) - 起价（取值为分组报名费中最低的值）
+ refund_type: 1 (number) - 退款策略：0 随时退款，1 报名截止前可退，2 不能退款
+ created: `2016-03-18 18:00:00` (string) - 创建时间
+ updated: `2016-03-18 18:00:00` (string) - 最后更新时间
+ state: 1 (number) - 赛事状态：-1 已关闭 0 取消 5 等待审核 10 被拒绝 15 审核中 20 进行中 100 已结束
+ covers(array[MatchCover]) - 海报列表
+ cover(object) - 封面
    + url: `http://avatar.qiniucdn.com/1.jpg`
    + sizes(array)
        + `!c256`
        + `!c512`
        + `!c1024`
+ groups(array[MatchGroup]) - 分组
+ my_state(MatchMemberSample) - 当前登录用户在此赛事的状态

## MatchSample(object)
+ id: 20 (number, required)
+ title: Match title (string)
+ cover(object) - 封面
    + url: `http://avatar.qiniucdn.com/1.jpg`
    + sizes(array)
        + `!c256`
        + `!c512`
        + `!c1024`
+ team_id: 1 (number) - 赛事主办方ID
+ team(TeamSample) - 赛事主办信息
+ user_id: 1000 (number) - 创建人ID
+ type: 0 (number) - 类型: 0 对战型，如：足球、蓝球， 1 非对战型，如：跑步、自行车
+ sports(array[number]) - 运动类型
+ contact: 张三 (string) - 联系方式
+ country: 中国 (string)
+ province: 四川 (string)
+ city: 成都 (string)
+ address: 天府软件园D区5栋羽毛球场 (string) - 赛事地址（注：由于赛事轮次可以单独设置地址，此地址可能是报名或总赛地址）
+ lat: 90.109879 (number)
+ lng: 104.559878 (number)
+ members_count: 100 (number) - 赛事报名总人数或团队数
+ comments_count: 20 (number) - 评论数
+ recommend_time: 1458530332 (number) - 推荐时间，被推荐的时间戳，推荐活动列表
+ recommend_region: 0 (number) - 推荐范围： 0 全国 1 同城
+ join_type: 0 (number) - 报名类型： 0 个人 1 团队
+ payment_type: 0 (number) - 支付方式： 0 线上支付 1 线下支付 2 均可
+ start_time: `2016-03-18 18:00:00` (string) - 开始时间
+ end_time: `2016-04-18 18:00:00` (string) - 结束时间
+ join_start: `2016-02-18 18:00:00` (string) - 报名开始时间，为空则表示通过审核后即可报名
+ join_end: `2016-03-05 18:00:00` (string)- 报名截止时间，为空则开始前均可报名
+ cancelled: `2016-03-18 18:00:00` (string) - 取消时间
+ cancel_reason: ` ` (string) 取消原因
+ verified: false (boolean) - 是否已认证
+ verify_reason: ` ` (string) - 认证原因
+ price: 20.00 (number) - 起价（取值为分组报名费中最低的值）
+ refund_type: 1 (number) -  退款策略：0 随时退款，1 报名截止前可退，2 不能退款
+ created: `2016-03-18 18:00:00` (string) - 创建时间
+ updated: `2016-03-18 18:00:00` (string) - 最后更新时间
+ state: 1 (number) - 赛事状态：-1 已关闭 0 取消 5 等待审核 10 被拒绝 15 审核中 20 进行中 100 已结束

## MatchMember(object)
+ id: 1 (number) 
+ user_id: 1000 (number) - 用户ID
+ order_id: 1002 (number) - 订单号
+ name: 王麻子 (string) - 名字
+ mobile: 138380038000 (string) - 联系电话
+ pt_order_no: 2016061788721 (string) - 订单号：如果状态是未支付，可以直接使用此订单号转支付
+ state: 0 (number) - 状态：0 待支付 1 待审核 10 正常

## MatchMemberSample(object)
+ id: 1 (number) 
+ user_id: 1000 (number) - 用户ID
+ name: 王麻子 (string) - 名字
+ pt_order_no: 2016061788721 (string) - 订单号：如果状态是未支付，可以直接使用此订单号转支付
+ state: 0 (number) - 状态：0 待支付 1 待审核 10 正常

## MatchOption(object)
+ match_id: 1 (number)
+ name: 昵称 (string) - 选项名称
+ field_type: text (string) - 选项类型
+ required: True (boolean) - 是否必填

## MatchAgainst(object)
+ left(MatchMemberSample) - 主场
+ right(MatchMemberSample) 李四 (string) - 客场
+ left_score: 1 (number) - 主场得分
+ right_score: 2 (number) - 客场得分
+ address: 天府软件园D区5栋羽毛球场 (string) - 比赛地址
+ start_time: `2016-04-18 18:00:00` (string) - 比赛时间

## MatchRound(object)
+ name: 第一轮 (string) - 轮次名称
+ start_time: `2016-03-18 18:00:00` (string) - 开始时间
+ end_time: `2016-04-18 18:00:00` (string) - 结束时间
+ address: `兴隆公园` (string) - 比赛地点
+ against_mapping(array[MatchAgainst]) - 对战列表，按时间先后顺序排列

## MatchStatus(object)
+ match_id: 1 (number)
+ content: 今天好日子 (string) 

## MatchStatusComment(object)
+ content: 好消息 (string)
+ user(User)

## Success(object)
+ status: ok (string)

## Error(object)
+ error: not found (string, required) - 错误描述
+ error_code: 404 (number, required) - 错误代码

## Error400(object)
+ error: arguments missing (string, required) - 错误描述
+ error_code: 400 (number, required) - 错误代码

## Error403(object)
+ error: 无权限  (string, required) - 错误描述
+ error_code: 403 (number, required) - 错误代码

## Error404(object)
+ error: not found (string, required) - 错误描述
+ error_code: 404 (number, required) - 错误代码

## Error401(object)
+ error: 未认证 (string, required) - 错误描述
+ error_code: 401 (number, required) - 错误代码


# Group 公共接口

### 获取七牛上传上传凭证 [GET /common/qiniu/upload_token{?type}]

`待定`

+ Parameters
    + type (string, required) - 上传类型：activty_cover, user_avatar, team_avatar

+ Response 200 (application/json)
    + Attributes
        + token: SHKXYQ (string) - 上传凭证
        + key: sdfadslfih123.png (string) - 上传文件KEY

### 获取中国省市列表 [GET /common/china_cities]

+ Response 200 (application/json)
    + Attributes
        + provinces(array)
            + province(object)
                + name: 北京 (string)
                + children(array)
                    + city(object)
                        + name: 东城区 (string)


### 获取运动类型列表 [GET /common/sports]

+ Response 200 (application/json)
    + Attributes
        + sports(array[Sport])

# Group 认证接口

## 请求手机验证码✓ [/auth/request_verify_code]

### 请求手机验证码 [POST]

+ 请求修改手机号短信验证码时需要提供密码

+ Request (application/json)
    + Attributes
        + mobile: 13838003800 (string, required)
        + action: login (string, required) - login, register_or_login, forgot, update_mobile
        + password: 123456 (string, required) - 请求修改手机号短信验证码时不能为空

+ Response 200 (application/json)
    + Attributes(Success)

## 使用手机号码注册或登录 [/auth/mobile]

### 使用手机号码注册或登录 [POST]

* 未注册手机将自己注册新用户
* 登录成功返回 `access_token`，同时将 `access_token` 存入 `cookie`，服务端需要先从 `header` 中获取 `X-Access-Token` 如果没有获取到
再从 `cooke` 中获取
* 客户端在请求时如果已登录无论是否需要登录的接口均需要在 `header` 中添加 `X-Access-Token`，值为此接口返回的 `access_token`

+ Request (application/json)
    + Attributes
        + mobile: 13838003800 (string, required)
        + verify_code: 8888 (string, required) - 通过  `请求手机验证码` 接口获取

+ Response 200 (application/json)
    + Attributes
        + user (User, required)
        + session(object)
            + access_token: ` ` (string)
            + token_secret: ` ` (string)

# Group 用户接口

## 用户 [/users{?limit,activity}]

### 获取用户信息 [GET /users/{user_id}]

获取别人用户信息时需要隐藏敏感信息

+ Parameters
    + user_id(number, required) - 用户ID

+ Response 200
    + Attributes (User)


### 当前用户信息 [GET /users/self]

当前登录用户信息

+ Response 200
    + Attributes (User)

### 修改用户资料 [PATCH /users/self]

密码和手机号不能通过此接口修改

+ Request
    + Attributes
        + name: Name (string)
        + dob: 1980-08-09 (string)
        + gender: f (string) - 性别：m 男， f 女

+ Response 200
    + Attributes(User)


### 修改用户手机 [PUT /users/self/mobile]

+ Request
    + Attributes
        + mobile: 1381380013800 (string, required)
        + verify_code: 8888 (string, required)

+ Response 200
    + Attributes(Success)


### 修改用户密码 [PUT /users/self/password]

+ Request
    + Attributes
        + oldpassword: 123456 (string) - 如果没有旧密码可以为空
        + newpassword: 654321 (string, required)

+ Response 200
    + Attributes(Success)


### 修改用户头像 [PUT /users/self/avatar]

待定上传模式：

+ 可以直接上传图片
+ 先上传到七牛再上传key
+ 获取上传头像的七牛上传策略然后通过七牛回调保存到用户信息中

+ Response 200
    + Attributes(Success)

### 用户报名活动列表 [GET /users/{user_id}/activities{?day,limit,page}]

每个场次一条记录，客户端应该在活动名称后加上场次日期

+ Parameters
    + user_id(number, required) - 用户ID
    + limit(number, optional) - 最多返回条数
    + page(number, optional) - 请求页数
    + day(string, optional) - 指定活动日期

+ Response 200 (application/json)
    + Attributes
        + activities(array[Activity])


### 修改活动报名资料 [PATCH /users/{user_id}/activities/{activity_id}/profile]

根据活动信息中要求的报名资料修改当前用的活动报名资料

+ Parameters
    + user_id(number, optional) - 用户ID
    + activity_id(number,optional) - 活动ID

+ Request (application/json)
    + Attributes
        + nickname: hello (string)

+ Response 201 (application/json)
    + Attributes(Success)

### 用户加入的俱乐部 [GET /users/{user_id}/teams{?limit,page}]

+ Parameters
    + user_id(number, optional) - 用户ID
    + limit(number, optional) - 最多返回条数
    + page(number, optional) - 请求页数

+ Response 200 (application/json)
    + Attributes
        + teams(array[Team])


### 用户在俱乐部内的资料 [GET /users/{user_id}/teams/{team_id}/profile]

+ Parameters
    + user_id(number, optional) - 用户ID
    + team_id(number,optional) - 俱乐部ID

+ Response 200 (application/json)
    + Attributes
        + nickname: hello (string) - 在俱乐部中的昵称
        + push_enabled: true (boolean) - 开启推送
        + credit: 100.00 (number) - 当前俱乐部余额

### 修改用户在俱乐部内的资料 [PATCH /users/{user_id}/teams/{team_id}/profile]

+ Parameters
    + user_id(number, optional) - 用户ID
    + team_id(number,optional) - 俱乐部ID

+ Request A (application/json)
    + Attributes
        + batch_id: 1 (number, required)
        + nickname: hello (string) - 在俱乐部中的昵称
        + push_enabled: true (boolean) - 开启推送
        + credit: 100.00 (number) - 当前俱乐部余额

+ Response 201 (application/json)
    + Attributes(Success)

### 用户账户变量记录 [GET /users/{user_id}/account_log{?team_id,limit,page}]

包含用户(余额)充值记录、消息记录、管理员对此成员余额的增减记录

+ Parameters
    + user_id(number, required) - 用户ID
    + team_id(number,optional) - 俱乐部ID
    + limit(number, optional) - 最多返回条数
    + page(number, optional) - 请求页数

+ Response 200 (application/json)

    + Attributes
        + account_log(array[AccountLog])


### 用户订单记录 [GET /users/self/orders{?team_id,type,state,limit,page}]

包含活动报名、实物订单，只能访问自己的订单列表

+ Parameters
    + team_id(number,optional) - 俱乐部ID，查询指定俱乐部内的订单
    + type(string, optional) - 订单类型, 可选值：all, activity,
    + state(number, optional) - 订单状态
    + limit(number, optional) - 最多返回条数
    + page(number, optional) - 请求页数

+ Response 200 (application/json)
    + Attributes
        + orders(array[Order])


### 订单详情 [GET /users/self/orders/{order_id}]

+ Parameters
    + order_id(number,required) - 订单ID（非订单号）

+ Response 200 (application/json)
    + Attributes(Order)

# Group 俱乐部

## 俱乐部 [/teams{?city,keyword,sport,sort,limit,page}]

### 获取俱乐部 [GET]

+ Parameters
    + city(string, optional) - 指定城市
    + keyword(string, optional) - 使用关键字搜索俱乐部
    + sport(string, optional) - 运动类型
    + sort(string, optional) - 排序方式
    + limit(number, optional) - 最多返回条数
    + page(number, optional) - 请求页数

+ Response 200 (application/json)
    + Attributes(array[Team])


### 新建俱乐部 [POST /teams]

每个用户只能创建一个俱乐部

+ Request (application/json)
    + Attributes(Team)

+ Response 200 (application/json)
    + Attributes(Team)

+ Response 403 (application/json)
    + Attributes(Error403)

## 俱乐部信息 [/teams/{team_id}]

+ Parameters
    + team_id(number, required) - 俱乐部ID

### 获取俱乐部信息 [GET]

+ Response 200 (application/json)
    + Attributes(Team)


### 修改俱乐部资料 [PATCH]

请求数据中只需要包含请求需要修改的属性

+ Request (application/json)
    + Attributes(Team)

+ Response 200 (application/json)
    + Attributes(Team)

### 修改俱乐部徽标 [PUT /teams/{team_id}/icon]

请求示例只供参考，boundary 的值一般会由请求库自动生成

+ Parameters
    - team_id (string, required)

+ Request (multipart/form-data; boundary=---BOUNDARY)

        -----BOUNDARY
        Content-Disposition: form-data; name="icon"; filename="icon.jpg"
        Content-Type: image/jpeg
        Content-Transfer-Encoding: base64

        /9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a
        HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIy
        MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIA
        AhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFAEB
        AAAAAAAAAAAAAAAAAAAAAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AL+AD//Z
        -----BOUNDARY

+ Response 200 (application/json)

    + 返回数据中`sizes`为一个数组，包含不同尺寸缩略图后缀，从小到大的顺序排列
    + 使用缩略图只需要选择合适尺寸的后缀添加到原地址结尾即可

    + Attributes
        + icon
            + url: http://imagecdn.com/team/1asdfasdf.png (string)
            + sizes(array)
                + !c128 (string) - 小尺寸后缀
                + !c512 (string) - 中尺寸后缀
                + !c1024 (string) - 大尺寸后缀


## 俱乐部活动 [/teams/{team_id}/activities{?limit,page}]

+ Parameters
    + team_id(number, required) - 俱乐部ID

### 获取俱乐部活动列表 [GET]

+ Parameters
    + team_id(number, required) - 俱乐部ID
    + limit(number, optional) - 最多返回条数
    + page(number, optional) - 请求页数

+ Response 200 (application/json)
    + Attributes
        + activities (array[Activity])

+ Response 404 (application/json)
    + Attributes(Error)

### 创建活动 [POST]

+ Request (application/json)
    + Attributes(Activity)

+ Response 200 (application/json)
    + Attributes(Activity)

### 删除俱乐部活动 [DELETE /teams/{team_id}/activities/{activity_id}]

+ Parameters
    + team_id(number, required) - 俱乐部ID
    + activity_id(number, required) - 活动ID

+ Response 204 (text/plain)


## 俱乐部成员 [/teams/{team_id}/members{?group}]

+ Parameters
    + team_id(number, required) - 俱乐部ID

### 俱乐部成员列表 [GET]

+ Parameters
    + group(number, optional) - 成员分组

+ Response 200 (application/json)
    + Attributes
        + members(array[User])

### 修改俱乐部成员信息 [PATCH /teams/{team_id}/members/{user_id}]

+ Parameters
    + team_id(number, required) - 俱乐部ID
    + user_id(number, required) - 用户ID

+ Request (application/json)
    + Attributes
        + group: Group name (string)
        + nickname: nick (string)

+ Response 201 (application/json)
    + Attributes(Success)


## 俱乐部成员分组 [/teams/{team_id}/member_groups]

+ Parameters
    + team_id(number, required) - 俱乐部ID

### 俱乐部成员分组列表 [GET]

+ Response 200 (application/json)
    + Attributes
        + groups(array[TeamMemberGroup])

### 添加俱乐部成员分组 [POST]

+ Request (application/json)
    + Attributes(TeamMemberGroup)

+ Response 200 (application/json)
    + Attributes(Success)

### 修改俱乐部成员分组 [PATCH /teams/{team_id}/member_groups/{group_id}]

+ Parameters
    + team_id(number, required) - 俱乐部ID
    + group_id(number, required) - 分组ID

+ Request (application/json)
    + Attributes
        + name: Group Name (string) - 不能重复

+ Response 200 (application/json)
    + Attributes(Success)

### 删除俱乐部成员分组 [DELETE /teams/{team_id}/member_groups/{group_id}]

如果分组内包含成员不允许删除

+ Parameters
    + team_id(number, required) - 俱乐部ID
    + group_id(number, required) - 分组ID

+ Response 204


### 加入俱乐部 [POST /teams/{team_id}/join]

+ Parameters
    + team_id(number, required) - 俱乐部ID

+ Response 200 (application/json)
    + Attributes(Success)

+ Response 202 (application/json)
    + Attributes
        + result: 等待审核 (string)

# Group 活动

## 活动 [/activities{?limit,page,team_id,sort}]

### 获取活动列表 [GET /activities{?limit,page,team_id,keyword,sport,sort,lat,lng,day}]

1. 如果没有指定日期则返回从当前时间开始的有场次的活动列表
2. 如果指定日期则返回指定日期有场次的活动列表

+ Parameters
    + team_id(number, required) - 俱乐部ID
    + keyword(string, optional) - 使用关键字搜索活动
    + sport(int, optional) - 运动类型
    + limit(number, optional) - 最多返回条数
    + page(number, optional) - 请求页数
    + lat(number, optional) - 纬度
    + lng(number, optional) - 经度
    + sort(string, optional) - 排序方式：newest, hottest, colsest
    + day(string, optional) - 日期：返回当天有场次的活动，day可以是日期范围

+ Response 200 (application/json)
    + Attributes
        + activities (array[Activity])

### 获取活动详情 [GET /activities/{activity_id}]

活动详情中需要包含场次列表

+ Parameters
    + activity_id(number, required) - 活动ID

+ Response 200
    + Attributes(Activity)

### 修改活动信息 [PATCH /activities/{activity_id}]

仅俱乐部管理员可以修改活动信息

+ Parameters
    + activity_id(number, required) - 活动ID

+ Request (application/json)
    + Attributes(Activity)

+ Response 200
    + Attributes(Activity)

### 报名参加活动 [POST /activities/{activity_id}/join]

请求数据需要包含活动中要求填写的身份资料

报名活动有以下几种情况：

1. 失败：人数已满、已经截止、没有资格报名（根据活动报名限制判断）
2. 成功：返回报名状态、支付状态及订单号等信息，如果需要支付根据用户选择支付方式调用对应支付接口

+ Parameters
    + activity_id(number, required) - 活动ID

+ Request (application/json)
     + Attributes
        + nickname: Nick name (string) - 昵称

+ Response 200 (application/json)
    + Attributes
        + state: wait_confirm (string) - 报名状态：cancelled 用户取消， wait_confirm 需要支付的活动未支付前, 不需要支付的活动如果需要审核的审核前为此状态，confirmed 支付成功或审核通过， rejected 拒绝， blocked 黑名单用户不允许再报名参加此活动  
        + payment_state: `WAIT_BUYER_PAY` (string) 
        + order_no: 2016032298121231 (number) - 订单号  


### 微信统一下单 [POST /orders/{order_no}/payment/wxpay/unifiedorder]

根据客户端提供的下单方式生成微信预支付订单信息
* 如果订单状态不是未支付将返回错误

+ Parameters
    + order_no(string, required) - 订单号

+ Request (application/json)
    + Attributes
        + order_no: 2016032298121231 (string, required) - 订单号
        + trade_type: 交易类型：NATIVE (string, required) - 交易类型：NATIVE(二维码支付) JSAPI(JS支付) APP(app支付)

+ Response 200 (application/json)
    + Attributes
        + appId: wx212312a (string)
        + timeStamp: 12312344 (number)
        + nonceStr: ldkjasdfqweradsfa (string)
        + package: `prepay_id=1231231241` (string)
        + signType: MD5 (string)
        + paySign: asdfalskdfjpwqr (string)
        + code_url: `wxpay://wqrq` (string) - 二维支付的内容


+ Response 403 (application/json)
    + Attributes(Error403)


### 支付宝支付 [POST /orders/{order_no}/payment/alipay]

根据客户端提供的下单方式生成支付宝支付需要的支付信息

* 如果订单状态不是未支付将返回错误

+ Parameters
    + order_no(string, required) - 订单号

+ Response 200 (application/json)
    + Attributes
        + paystr: wx212312a (string)


### 活动报名表 [GET /activities/{activity_id}/members}]

活动报名成员列表

+ Parameters
    + activity_id(number, required) - 活动ID

+ Response 200 (application/json)
    + Attributes
        + members(array[User])

# Group 赛事

### 赛事列表 [GET /matches{?limit,page,team_id,keyword,sport,sort,lat,lng,day}]

+ Parameters
    + team_id(number, optional) - 俱乐部ID
    + keyword(string, optional) - 使用关键字搜索活动
    + sport(int, optional) - 运动类型
    + limit(number, optional) - 最多返回条数
    + page(number, optional) - 请求页数
    + sort(string, optional) - 排序方式：newest, hottest, colsest

+ Response 200 (application/json)
    + Attributes
        + num_pages: 10 (number) - 总页数
        + previous_page: 1 (number) - 上一页
        + current_page: 2 (number) - 当前页码
        + next_pate: 3 (number) - 下一页
        + total: 200 (number) - 总数
        + per_page: 20 (number) - 每页返回数
        + matches (array[MatchSample])
        
        
### 赛事详情 [GET /matches/{match_id}]

包含以下信息 
    赛事基本信息
    海报列表
    分组和价格

特别说明：  
赛事状态如果为`进行中(20)`需要根所其它属性计算以下状态： 

    `准备报名` 报名开启前
    `正在报名` 报名截止和报满之前
    `已报满` 所有分组都已报满
    `已截止` 报名截止之后
    `进行中` 报名开始之后状态非已结束

+ Parameters
    + match_id(number, required) - 赛事ID

+ Response 200 (application/json)
    + Attributes(Match)


### 赛事报名表单 [GET /matches/{match_id}/apply_form]

赛事报名表单选项列表
报名表单选项分两部分：
1. 系统选项（数组），可能值为 name 名称，gender 性别，age 年龄，mobile 手机，avatar 头像，  
idcard_number 证件号码， idcard_photo 证件照片
   系统选项需要特殊处理，需要使用用户信息自动填充，证书照片需要设计为上传正反面  
   
2. 自定义选项：field_type 可能值为：text 文本（单行），textarea 多行文本，number 数字，choice 单选，multichoice 多选，photo 照片，file 文件  

+ Parameters
    + match_id(number, required) - 赛事ID

+ Response 200 (application/json)
    + Attributes
        + options(array[string]) - 系统选项
        + custom_options(array[MatchOption]) - 自定义选项

### 赛事报名 [POST /matches/{match_id}/join]

`需要已登录`

提交报名资料生成成员信息和订单信息

`注意：因为需要需要上传文件，此接口不使用json提交，提交类型为 multipart/form-data`  
  
文档编辑器原因请求请求示例仍然显示为 `json`，但请求时使用 `multipart/form-data`

说明：
1. 对于系统选项提交 `key` 为报名表单列表中`options`的值，如名称的 key 为 `name`,
证件照片(`idcard_photo`) 比较特殊需要使用两个字段上传：`idcard_front` 和 `idcard_back` 分别上传正面和背面照片  
2. 自定义选项所有 `key` 为 `option_`+`custom_option_id`，如 `option_1000`
3. 需要提交的信息由 报名表单选项列表决定，此接口说明示例只做参考 

+ Parameters
    + match_id(number, required) - 赛事ID

+ Request (multipart/form-data)
    + Attributes
        + group_id(number, required) - 报名分组ID
        + name(string) - 名称
        + gender(string) - 性别：f 女 m 男
        + mobile(string) - 联系电话
        + avatar(string) - 头像
        + idcard_number(string) - 证件号码 
        + idcard_front(string) - 证件照片正面(文件类型)
        + idcard_back(string) - 证件照片背面(文件类型)
        + option_100(string)
        + option_101(string)
        + option_102(string)

        
+ Response 200 (application/json)
    + Attributes(Success)

### 赛事轮次列表 [GET /matches/{match_id}/rounds]

对战类型赛事每个轮次包含对战列表、非对战类型为本轮次参赛成员列表

+ Parameters
    + match_id(number, required) - 赛事ID

+ Response 200 (application/json)
    + Attributes
        + rounds(array[MatchRound])

### 赛事动态列表 [GET /matches/{match_id}/statuses]

赛事战报列表

+ Parameters
    + match_id(number, required) - 赛事ID
    
+ Response 200 (application/json)
    + Attributes
        + statuses(array[MatchStatus])
        
## 赛事报名列表 [/matches/{match_id}/members]

### 获取完整报名列表 [GET]

+ Parameters
    + match_id(number, required) - 赛事ID
    
+ Response 200 (application/json)
    + Attributes
        + members(array[MatchMember])

### 修改赛事报名资料 [GET /matches/{match_id}/profile]

+ Parameters
    + match_id(number, required) - 赛事ID
    
+ Response 200 (application/json)
    + Attributes(Success)


## 用户赛事 [/users/{user_id}/matches]

### 获取列表 [GET]

+ Parameters
    + user_id(number, required) - 用户ID
    
+ Response 200 (application/json)
    + Attributes
        + matches(array[MatchSample])
