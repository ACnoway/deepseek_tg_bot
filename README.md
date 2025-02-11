一个用chatgpt和自己的一点脑子搓出来的对接deepseek api的telegram机器人，目前对接的是百度云的api，可以自行在代码中更改。

寒假正好赶上deepseek爆火，结果找了一圈很多之前的telegram机器人后端都还没适配（百度云当时有个功能还没出，导致别的对接一直报错），于是想靠着chatgpt手搓一个出来，目前还不完善，支持功能如下：

1. 唤醒功能：群聊内使用需在消息最开始加唤醒词来唤醒机器人，私聊模式下不用
2. 记忆功能：对每个用户单独存储，群聊内和私聊内记忆互通，发送 `/reset` 可以消除记忆，默认使用前15条记忆，这个数量暂时不能改
3. 选择模型：在消息开头（唤醒词后）加 `r1` 可以使用 deepseek-r1 模型
4. 白名单：根据telegram的uuid判断用户是否在白名单内，若不在则发出提醒

还没来得及做的大概有更改记忆条数，为每个人增加自定义模板等，之后等到api出了适配之后还会做token计算之类的，现在star入股不亏（狗头

## 使用说明

1. 先去 @botfather 新建一个bot并将其的token填写至代码标识处
2. 将自己的apikey填入代码标识处
3. （若开启白名单的话）同目录下新建一个 `whitelist.json` 文件，并以以下格式将uuid填入文件中：`["uuid1","uuid2","uuid3"]`
4. 运行此文件，给bot发消息等待bot回复即可