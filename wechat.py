# coding:utf-8

from flask import Flask, request, abort, render_template
import hashlib
import xmltodict
import time
# 用它可以访问http请求地址
import urllib2
import json

# 常量
# 微信的token令牌
WECHAT_TOKEN = "xiaoge"
# appid
WECHAT_APPID = "wx92004523d28535e8"
# appsecret
WECHAT_APPSECRET = "a58cf031df24cb4d03fc25cb9cdcf44a"

app = Flask(__name__)


# 这是微信服务器访问的
@app.route("/wechat8001", methods=["GET", "POST"])
def wechat():
    """对接微信公众号服务器"""
    # 验证服务器地址的有效性
    # 开发者提交信息后，微信服务器将发送GET请求到填写的服务器地址URL上，GET请求携带四个参数:
    # signature:微信加密, signature结合了开发者填写的token参数和请求中的timestamp参数 nonce参数
    # timestamp:时间戳(chuo这是拼音)
    # nonce: 随机数
    # echostr: 随机字符串


    # 接收微信服务器发送参数
    signature = request.args.get("signature")
    timestamp = request.args.get("timestamp")
    nonce = request.args.get("nonce")

    # 校验参数
    # 校验流程：
    # 将token、timestamp、nonce三个参数进行字典序排序
    # 将三个参数字符串拼接成一个字符串进行sha1加密
    # 开发者获得加密后的字符串可与signature对比，标识该请求来源于微信


    if not all([signature, timestamp, nonce]):
        # 抛出400错误
        abort(400)

    # 按照微信的流程计算签名
    li = [WECHAT_TOKEN, timestamp, nonce]

    # 排序
    li.sort()

    # 拼接字符串
    tmp_str = "".join(li)

    # 进行sha1加密, 得到正确的签名值
    sign = hashlib.sha1(tmp_str).hexdigest()

    # 将自己计算的签名值, 与请求的签名参数惊醒对比, 如果相同, 则证明请求来自微信
    if signature != sign:
        # 代表请求不是来自微信
        # 弹出报错信息, 身份有问题
        abort(403)
    else:
        # 表示是微信发送的请求
        if request.method == "GET":
            # 表示第一次接入微信服务器的验证
            echostr = request.args.get("echostr")
            # 校验echostr
            if not echostr:
                abort(400)
            return echostr

        elif request.method == "POST":
            # 表示微信服务器转发消息过来
            # 拿去xml的请求数据
            xml_str = request.data

            # 当xml_str为空时
            if not xml_str:
                abort(400)

            # 对xml字符串进行解析成字典
            xml_dict = xmltodict.parse(xml_str)

            xml_dict = xml_dict.get("xml")

            # MsgType是消息类型 这里是提取消息类型
            msg_type = xml_dict.get("MsgType")

            if msg_type == "text":
                # 表示发送文本消息
                # 第一次要么回复你想回复的内容, 不知道回复什么, 微信说了要么回复success, 要么空字符串
                # 够造返回值, 经由微信服务器回复给用户的消息内容
                # 回复消息
                # ToUsername: (必须传) 接收方账号(收到的OpenID)
                # FromUserName: (必须传) 开发者微信号
                # CreateTime: (必须传) 消息创建时间(整形)
                # MsgType: (必须传) 消息类型
                # Content: (必须传) 回复消息的内容(换行:在Content中能够换行, 微信客户端就支持换行显示)

                resp_dict = {
                    "xml":{
                        "ToUserName":xml_dict.get("FromUserName"),
                        "FromUserName":xml_dict.get("ToUserName"),
                        "CreateTime":int(time.time()),
                        "MsgType":"text",
                        "Content":xml_dict.get("Content")
                    }
                }
            else:
                resp_dict = {
                    "xml": {
                        "ToUserName": xml_dict.get("FromUserName"),
                        "FromUserName": xml_dict.get("ToUserName"),
                        "CreateTime": int(time.time()),
                        "MsgType": "text",
                        "Content": "I LOVE YOU"
                    }
                }
            # 将字典转换为xml字符串
            resp_xml_str = xmltodict.unparse(resp_dict)
            # 返回消息数据给微信服务器
            return resp_xml_str

# 这是用户通过微信访问的 这里只能通过域名访问
# www.itcastcpp.cn/wechat8001/index
@app.route("/wechat8001/index")
def index():
    """让用户通过微信访问的网页页面视图"""

    # 用户同意授权，获取code
    # 让用户访问一下链接地址：
    # https: // open.weixin.qq.com / connect / oauth2 / authorize?
    # appid = APPID & redirect_uri = REDIRECT_URI & response_type = code &
    # scope = SCOPE & state = STATE  # wechat_redirect

    # 参数        是否必须            说明
    # appid         是              公众号唯一标识
    # redirect_uri  是              授权后的回调链接地址, 请使用urlencode对连接进行处理
    # response_type 是              返回类型, 请填写code
    # scope         是              应用授权作用域snsapi_base, (不弹出授权页面直接跳转, 只能获取用户openid)
    #                               snsapi_userinfo(弹出授权页面, 可通过openid拿到昵称, 性别, 所在地,
    #                               并且, 即使在未关注的情况下, 只要用户授权, 也能获取其信息)
    # state         否              从定向后会带上state参数, 开发者可以填写a-zA-Z0-9的参数值, 最多128字节
    # #wechat_redirect  是          无论直接打开还是做页面302重定向的时候, 必须带此参数

    # 从微信服务器中拿去用户的资料数据
    # 1. 提取code参数
    code = request.args.get("code")

    # 用户同意授权后
    # 如果用户同意授权，页面将跳转至
    # redirect_uri /?code = CODE & state = STATE。若用户禁止授权，
    # 则重定向后不会带上code参数，仅会带上state参数redirect_uri?state = STATE
    if not code:
        return "Missing code parameters"



    # 2. 向微信服务器发送http请求回去access_token
    # 通过code换取网页授权access_token
    # 请求方法
    # https: // api.weixin.qq.com / sns / oauth2 / access_token?appid = APPID &
    # secret = SECRET & code = CODE & grant_type = authorization_code
    # 参数                  是否必须                说明
    # appid                 是                    公众号唯一标识
    # secret                是                    公众号的appsecret
    # code                  是                    填写第一步获取code参数
    # grant_type            是                    填写为authorization_type


    url = "https://api.weixin.qq.com/sns/oauth2/access_token?appid=%s&secret=%s&code=%s&grant_type=authorization_code"%(WECHAT_APPID, WECHAT_APPSECRET, code)


    # 使用urllib2.urlopen方法发送请求
    # 如果只传网址的url参数, 则默认使用http的get请求方式, 返回响应对象
    response = urllib2.urlopen(url)

    # 获取相应体数据, 这是微信返回的json数据
    json_str = response.read()
    # 返回值
    # 正确时返回的JSON数据包如下：
    #
    # {
    #     "access_token": "ACCESS_TOKEN",
    #     "expires_in": 7200,
    #     "refresh_token": "REFRESH_TOKEN",
    #     "openid": "OPENID",
    #     "scope": "SCOPE"
    # }

    # 参数                        参数描述
    # access_token               网页授权接口调用凭证, 注意,此access_token与基础支持的access_token不同
    # expires_in                 access_token接口调用凭证超时时间, 单位(秒)
    # refresh_token              用户刷新access_token
    # openid                     用户唯一标识, 请注意, 在未关注公众号时, 用户访问公众号的页面, 也会产生一个用户和公众号唯一的openid
    # scope                      用户授权的作用域, 使用逗号(,)分隔

    # 错误时微信会返回JSON数据包如下（示例为Code无效错误）:
    #
    # {
    #     "errcode": 40029,
    #     "errmsg": "invalid code"
    # }



    # 把json字符串解析成python里面的字典
    resp_dict = json.loads(json_str)

    # 获取access_token, openid
    if "errcode" in resp_dict:
        return "Failed to get access_token parameter"

    access_token = resp_dict.get("access_token")
    openid = resp_dict.get("openid")




    # 3. 向微信服务器发送http请求, 获取用户的资料数据
    # 拉取用户信息(需scope为snsapi_userinfo)
    # 请求方法
    # https: // api.weixin.qq.com / sns / userinfo?access_token = ACCESS_TOKEN
    # & openid = OPENID & lang = zh_CN
    # 参数                    描述
    # access_token           网页授权接口调用凭证, 注意,此access_token与基础支持的access_token不同
    # openid                 用户的唯一标识
    # lang                   返回国家地区预言版本, zh_CN简体, zh_TW繁体, en英语

    url = "https://api.weixin.qq.com/sns/userinfo?access_token=%s&openid=%s&lang=zh_CN"%(access_token, openid)
    response = urllib2.urlopen(url)
    # 读取微信传回的json的响应体数据
    user_json_str = response.read()
    user_dict_data = json.loads(user_json_str)
    # 返回值
    # 正确时返回的JSON数据包如下：
    #
    # {
    #     "openid": " OPENID",
    #     " nickname": NICKNAME,
    #     "sex": "1",
    #     "province": "PROVINCE",
    #     "city":"CITY",
    #     "country":"COUNTRY",
    #     "headimgurl":"http://wx.qlogo.cn/mmopen/g3MonUZtNHkdmzicIlibx6iaFqAc56vxLSUfpb6n5WKSYVY0ChQKkiaJSgQ1dZuTOgvLLrhJbERQQ4eMsv84eavHiaiceqxibJxCfHe/46",
    #     "privilege":[
    #      "PRIVILEGE1",
    #      "PRIVILEGE2"
    #      ],
    #      "unionid": "o6_bmasdasdsad6_2sgVt7hMZOPfL"
    # }

    # 参数                            描述
    # openid                         用户唯一标识
    # nickname                       用户昵称
    # sex                            用户的性别, 值为1时男性, 值为2时女性, 值为0时是未知
    # province                       用户个人资料填写的省份
    # city                           普通用户个人资料填写的城市
    # country                        国家, 如中国为CN
    # headimgurl                     用户头像, 最后一个值代表正方形头像大小(0 ,46, 64, 96,
    #                                132数值可选, 0代表640*640头像), 用户没有头像时该项为空.
    #                                若用户跟换头像,原有头像url将失效.
    # privilege                      用户特权信息, json数组, 如微信沃卡用户为(chinaunicom)
    # unionid                        只有在用户将公众号绑定到微信开放平台账号后, 才会出现该字段.
    #                                详见:获取用户个人信息(UnionID机制)

    # 错误时微信会返回JSON数据包如下:
    #
    # {
    #     "errcode": 40003,
    #     "errmsg": " invalid openid "
    # }


    # 判断微信返回的是不是错误的json
    if "errcode" in user_dict_data:
        return "Failed to obtain user information"

    # 将用户的资料数据填充到页面中
    return render_template("index.html", user=user_dict_data)


if __name__ == '__main__':
    app.run(port=8001, debug=True)