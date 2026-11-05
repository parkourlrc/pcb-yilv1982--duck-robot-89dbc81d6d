# 产品图鉴媒体归档与权利说明

截止／归档日：2026-10-10。供[41卡图鉴](../product-atlas.md)、[研究报告](../research.md)和[新增U证据](../evidence.md#atlas-sources)使用；完整、无字段删减的机器可读记录为[manifest.json](manifest.json)。现为43项媒体记录（原42＋X11主图1），覆盖41个研究对象，不是43款产品。

## 数量、路径与版本

| 分组 | 产品卡 | 本地JPEG | 官方视频链接 | 原始分片清单 |
|---|---:|---:|---:|---|
| G1 | 10 | 12（10主图＋2张AIBI图文证据） | 0 | [media-g1.json](../parts/media-g1.json) |
| G2 | 10 | 10 | 0 | [media-g2.json](../parts/media-g2.json) |
| G3 | 10 | 8 | 2 | [media-g3.json](../parts/media-g3.json) |
| G4 | 10 | 8 | 2 | [media-g4.json](../parts/media-g4.json) |
| G5 | 1 | 1 | 0 | [Microduck补片](../parts/microduck-market-2026.md)／[D102](../evidence.md#d102) |
| 合计 | **41唯一product_id** | **39** | **4** | 原42记录逐项保留＋X11主图1 |

- JSON中的`local_path`以专题根目录为基准（如`media/g1/ad01.jpg`），不是从本README再拼一层media；下表链接则按本README位置解析。
- 只按manifest列出的实际路径发布，不扫描目录把临时文件或原始大图自动打包。主会话已回传独立程序核验：38图均在media内、SHA-256／宽高／字节与分片JSON一致，长边≤1200，总2,360,883 bytes，g*下无未索引多余图。此为主会话结果，集成者不冒称亲自做了该项独立验收。
- 本地JPEG是来源图片的轻量研究引用副本，不一定是原始文件的逐字节副本。各条保留原始URL、处理方式、尺寸和本地SHA-256；G1等提供的源哈希／源尺寸、G3的内嵌图定位等附加字段均在JSON完整保留。没有源哈希的项不补造，也不冒称源图已永久归档。

## 权利与验证范围

**原图版权不开放；仅作本报告产品辨识、必要评论与研究的最小引用，不授予商业再分发、素材库、模型训练或去水印权利。** 著作权、商标和角色IP归各原权利人，仓库代码许可不覆盖这些素材；本说明不是从公开可访问性推定获得开放授权。具体publisher／rights／processing／limitations优先按逐条JSON及U证据读取。

- 图片来源为外部官网、商店、官方历史发布或厂商供稿素材；可能是渲染、合成或宣传场景，**不是本项目拍摄、消费者签收、硬件拆解或功能验收**。不覆写分片原图文件，也不生成替代产品图片。
- 图片的`verified=true`表示原采集角色核对了来源／对应代际和图像预览，不代表AI算法、性能、隐私或销售已验收。
- 视频的`verified=true`仅表示元数据／静态页面核对，不能等同观看完成；G3两条未播放。G4两条的`verification_scope`统一为“仅核标题/频道/简介/发布时间及播放器静态起始画面；未播放验证动态内容，不作动作连续性/性能/2026供货证据”。四条均无动态内容实测。视频无本地文件、不下载／转码／截取封面，仅保留外链，不嵌入远程播放器；链接将来可能失效。
- Uni与Paradise的产品图因Bandai转载限制未下载；以官方视频外链保留核验入口。Hello Barbie仅55×110官方缩略图，保留尺寸，不放大作高清硬件图。Bitzee使用2023原版紫盒新闻图，不用商品页错配的Magicals绿盒。
- Romi代表图为Lacatan自然白，Toniebox为2代Moon Grey；不代表初代或系列年度统计。MicroPets锁定GEN1 Cat的JAN4904810947202，不把M08类别销售归到该SKU；Sweekar成长图是众筹期厂商供稿，非一台机器的连续量产实拍。CoCo是Beta预约图，50是预约名额。
- AIBI人脸／天气两张图文证据计素材不加产品数；ROYBI的内嵌data图没有独立图片HTTP URL，保留原字段为空及DOM定位。bibo未使用禁止转载的OFweek图片，改取厂商主页素材；具体限制均保留。

## 逐项来源索引

表面仅列对象、版本、引用文件和来源页；**每项完整asset_url／video_url、publisher、访问日、权利限制、处理、验证范围和校验值见[JSON详情](manifest.json)**。图片来源页及直链不同，不能将来源页URL当作原始图片URL。

| 产品／素材 | 本地引用或官方视频 | 对象／具体版本 | 来源页 |
|---|---|---|---|
| [AD01](../product-atlas.md#card-ad01) · aibo ERS-1000 官方首页主视觉 | [g1/ad01.jpg](g1/ad01.jpg) | ERS-1000 | [Sony](https://aibo.sony.jp/) |
| [AD02](../product-atlas.md#card-ad02) · LOVOT 3.0 技术页本体图 | [g1/ad02.jpg](g1/ad02.jpg) | LOVOT 3.0 | [GROOVE X](https://lovot.life/technology/) |
| [AD03](../product-atlas.md#card-ad03) · Moflin PE-M10 发布图 | [g1/ad03.jpg](g1/ad03.jpg) | PE-M10GD / PE-M10SR | [CASIO](https://www.casio.co.jp/release/2024/1010-moflin/) |
| [AD04](../product-atlas.md#card-ad04) · Qoobo HUSKY GRAY 大号 | [g1/ad04.jpg](g1/ad04.jpg) | Qoobo YE-QB001G（非Petit） | [Yukai Engineering](https://store.ux-xu.com/products/qoobo) |
| [AD05](../product-atlas.md#card-ad05) · Mirumi Gray 官方本体近照 | [g1/ad05.jpg](g1/ad05.jpg) | Mirumi Gray | [Yukai Engineering](https://store-jp.mirumi.tokyo/) |
| [AD06](../product-atlas.md#card-ad06) · Eilik Blue 基础单机 | [g1/ad06.jpg](g1/ad06.jpg) | Eilik Blue（非DQ、无AI Station） | [Energize Lab](https://store.energizelab.com/products/eilik) |
| [AD07](../product-atlas.md#card-ad07) · EMO 基础套装官方商品图 | [g1/ad07.jpg](g1/ad07.jpg) | EMO LA20401011 | [LivingAI](https://living.ai/product/emo/) |
| [AD08](../product-atlas.md#card-ad08) · AIBI Pocket 官方商品图 | [g1/ad08.jpg](g1/ad08.jpg) | AIBI Pocket LA23101011 | [LivingAI](https://living.ai/product/aibi-pocket/) |
| [AD09](../product-atlas.md#card-ad09) · Loona Petbot Premium 商品图库图1 | [g1/ad09.jpg](g1/ad09.jpg) | Loona Petbot Premium（非Space Edition、非DeskMate） | [KEYi / KEYi Robot](https://keyirobot.com/en-sg/products/petbot) |
| [AD10](../product-atlas.md#card-ad10) · Vector 2.0 黑色当前商品图 | [g1/ad10.jpg](g1/ad10.jpg) | Vector 2.0 黑色新机 | [ANKI 当前品牌运营站](https://anki.bot/products/vector-robot) |
| [AD08](../product-atlas.md#card-ad08) · AIBI Pocket 官方图文：认脸与拍照 | [g1/ad08-feature-face.jpg](g1/ad08-feature-face.jpg) | AIBI Pocket LA23101011 | [LivingAI](https://living.ai/product/aibi-pocket/) |
| [AD08](../product-atlas.md#card-ad08) · AIBI Pocket 官方图文：天气动画 | [g1/ad08-feature-weather.jpg](g1/ad08-feature-weather.jpg) | AIBI Pocket LA23101011 | [LivingAI](https://living.ai/product/aibi-pocket/) |
| [AD11](../product-atlas.md#card-ad11) · Robosen G1 Elite 擎天柱卡车形态官方商品图 | [g2/ad11.jpg](g2/ad11.jpg) | G1 Elite 美国店展示；非 Flagship、电影版或拖车，不证明中国 SKU 细节完全相同 | [Robosen；TRANSFORMERS IP 属 Hasbro 等权利人](https://us.robosen.com/products/robosen-elite-optimus-prime) |
| [AD12](../product-atlas.md#card-ad12) · Ropet KAMOMO Pro 套件商品图 | [g2/ad12.jpg](g2/ad12.jpg) | 当前 KAMOMO Pro 套件，非 Basic 或早期众筹配置 | [Ropet](https://ropetai.com/products/ropet%E2%84%A2-ai-comfort-companion-plush-robot) |
| [AD13](../product-atlas.md#card-ad13) · FoloToy Kumma / 乐乐小熊官方商品图 | [g2/ad13.jpg](g2/ad13.jpg) | 当前 Kumma/乐乐消费套件；非 Panda/Momo | [FoloToy](https://store.folotoy.com/products/folotoy-ai-teddy) |
| [AD14](../product-atlas.md#card-ad14) · BubblePal 官方挂件宣传图 | [g2/ad14.jpg](g2/ad14.jpg) | BubblePal 挂件；不锁定 6 个销售变体之一 | [Haivivi](https://www.haivivi.cn/product/bubblepal) |
| [AD15](../product-atlas.md#card-ad15) · CocoMate 奥特曼官方产品图 | [g2/ad15.jpg](g2/ad15.jpg) | CocoMate 奥特曼三款外观与电子模块同框；599 CNY 为单件页面价，不代表三只套装 | [Haivivi；奥特曼 IP 属相应权利人](https://shop161889777.m.youzan.com/wscgoods/detail/26w0slv0c2bxlvm) |
| [X01](../product-atlas.md#card-x01) · Sweekar 厂商 Takway 提供的发布照片 | [g2/x01.jpg](g2/x01.jpg) | 2026 众筹期发布素材，非量产验收图 | [Takway 提供，TechAcute 刊载](https://techacute.com/sweekar-pocket-ai-pet-that-grows/) |
| [X02](../product-atlas.md#card-x02) · KOTTI 灰脸版本体发布图 | [g2/x02.jpg](g2/x02.jpg) | 日本先行销售 KOTTI 灰脸本体；固件版本未知 | [未来MD株式会社提供，@Press 刊载](https://www.atpress.ne.jp/news/599376) |
| [X03](../product-atlas.md#card-x03) · Tuya CES 2026 蜂窝版 Fuzozo 展示插图 | [g2/x03.jpg](g2/x03.jpg) | Tuya CES 2026 蜂窝版展示素材，非未经核实的美国站 SKU 或交付实拍 | [Tuya Smart / Robopoet](https://www.tuya.com/news-details/Kf9n2k7vvbj1y) |
| [X04](../product-atlas.md#card-x04) · Loona DeskMate Obsidian 官方商品图 | [g2/x04.jpg](g2/x04.jpg) | DeskMate Obsidian 手机运动底座，非 Loona Petbot | [KEYi Tech](https://keyirobot.com/en-no/products/deskmate) |
| [X05](../product-atlas.md#card-x05) · 镭萌 bibo 官方主页产品图 | [g2/x05.jpg](g2/x05.jpg) | bibo 官方主页展示款，非硬件批次/量产版本认证 | [杭州镭萌科技有限责任公司](https://moe-lab.com/) |
| [F01](../product-atlas.md#card-f01) · Miko 3红色款官方产品图 | [g3/f01.jpg](g3/f01.jpg) | Miko 3；非Miko Mini | [Miko](https://miko.ai/products/miko-3) |
| [F02](../product-atlas.md#card-f02) · Moxie新运营方官网机身宣传图 | [g3/f02.jpg](g3/f02.jpg) | Moxie既有硬件形象；新运营方首页宣传，非新款发布 | [Moxie Robots, Inc.](https://moxierobots.com/) |
| [F03](../product-atlas.md#card-f03) · ROYBI可换彩色帽子官方页面嵌入图 | [g3/f03.jpg](g3/f03.jpg) | 原ROYBI Robot；非网页App截屏 | [ROYBI / roybi.world](https://roybi.world/) |
| [F04](../product-atlas.md#card-f04) · Furby2023 Purple F6743官方支持图 | [g3/f04.jpg](g3/f04.jpg) | Furby2023 Purple F6743；非Connect/Furblets | [Hasbro](https://instructions.hasbro.com/en-gb/instruction/furby-purple-plush-interactive-toys-for-6-year-old-girls-boys-up) |
| [F05](../product-atlas.md#card-f05) · Hatchimals Alive Mystery Hatch Draggle产品图 | [g3/f05.jpg](g3/f05.jpg) | Mystery Hatch Draggle；非迷你水孵化系列 | [Spin Master](https://www.spinmaster.com/en-US/brands/hatchimals/hatchimals-alive-mystery-hatch-draggle-styles-may-vary/) |
| [F06](../product-atlas.md#card-f06) · 2023 Bitzee原版紫盒与包装官方首发新闻图 | [g3/f06.jpg](g3/f06.jpg) | Bitzee原版紫盒15宠物；非Magicals/Disney | [Spin Master / CNW](https://spinmaster.mediaroom.com/2023-06-22-Spin-Master-Descends-on-VidCon-Welcoming-Attendees-to-Be-Among-the-First-to-Get-Their-Hands-on-Bitzee) |
| [F07](../product-atlas.md#card-f07) · Buy a Tamaverse Ticket and Enter the Tama Portal! | [官方视频外链](https://www.youtube.com/watch?v=_zBue18zkdA) | Tamagotchi Uni票券功能；非Paradise | [Tamagotchi US](https://tamagotchi-official.com/us/series/uni/video/) |
| [F08](../product-atlas.md#card-f08) · Hello Barbie DKF74官方支持页缩略图 | [g3/f08.jpg](g3/f08.jpg) | Hello Barbie DKF74，2015 | [Mattel](https://service.mattel.com/us/productDetail.aspx?prodno=DKF74&siteid=27) |
| [X09](../product-atlas.md#card-x09) · 【Tamagotchi Paradise】Tamagotchi Paradise商品PV【たまごっち】 | [官方视频外链](https://www.youtube.com/watch?v=M-gZZClFCkY) | 2025首发Tamagotchi Paradise；非Neon Planets/My Lab Tamagotchi | [たまごっち/Tamagotchi【公式】](https://tamagotchi-official.com/jp/series/paradise/video/?p=2) |
| [X10](../product-atlas.md#card-x10) · マイクロペット GEN1 キャット官方产品图 | [g3/x10.jpg](g3/x10.jpg) | 2025日本新系列GEN1 Cat，JAN4904810947202；非早期同名代际 | [TOMY / The Moose Group](https://www.takaratomy.co.jp/products/micropets/) |
| [F09](../product-atlas.md#card-f09) · Sphero BOLT 原版透明球主图 | [g4/f09.jpg](g4/f09.jpg) | BOLT 原版 K002ROWFFP，非BOLT+ | [Sphero](https://sphero.com/products/sphero-bolt) |
| [F10](../product-atlas.md#card-f10) · Dash与编程界面宣传图 | [g4/f10.jpg](g4/f10.jpg) | Dash SKU1-DA03-11，非Cue/Dot | [Wonder Workshop / MORAVIA Education](https://moravia-education.com/products/dash) |
| [F11](../product-atlas.md#card-f11) · Ozobot Evo 手工主题场景 | [g4/f11.jpg](g4/f11.jpg) | Evo，Entry Kit SKU050110-01对应机型；非Bit/Ari | [Ozobot](https://ozobot.com/products/evo-entry-kit-1) |
| [F12](../product-atlas.md#card-f12) · Meet mBot2 | [官方视频外链](https://www.youtube.com/watch?v=uxpoP175mOU) | mBot2 CyberPi代，与mBot Neo同分类，非mBot1/Rover | [xTool Education](https://www.youtube.com/watch?v=uxpoP175mOU) |
| [F13](../product-atlas.md#card-f13) · LEGO 51515五种主模型展示 | [g4/f13.jpg](g4/f13.jpg) | MINDSTORMS Robot Inventor 51515，2020官方发布图 | [LEGO Group](https://www.lego.com/en-us/aboutus/news/2020/june/lego-mindstorms-robot-inventor) |
| [F14](../product-atlas.md#card-f14) · SPIKE Prime 45678课堂机构实验 | [g4/f14.jpg](g4/f14.jpg) | SPIKE Prime 45678，非Essential | [LEGO Education](https://education.lego.com/en-us/products/lego-education-spike-prime-set/45678/) |
| [F15](../product-atlas.md#card-f15) · The Ultimate Clicbot Official Video | [官方视频外链](https://www.youtube.com/watch?v=PalRN6ylCW8) | ClicBot 2020宣传版，非Loona | [LOONA PETBOT](https://www.youtube.com/watch?v=PalRN6ylCW8&themeRefresh=1) |
| [X06](../product-atlas.md#card-x06) · AOGU CoCo 先行预约版宣传图 | [g4/x06.jpg](g4/x06.jpg) | AOGU CoCo 2026 Beta先行预约版 | [AOGU株式会社（PR TIMES企业稿提供）](https://prtimes.jp/main/html/rd/p/000000007.000166793.html) |
| [X07](../product-atlas.md#card-x07) · Romi Lacatan自然白代表图，不代表全系列统计 | [g4/x07.jpg](g4/x07.jpg) | Lacatan自然白；非P01/P02或Hello Kitty型 | [MIXI / Romi](https://shop.romi.ai/products/romi-lacatan) |
| [X08](../product-atlas.md#card-x08) · Toniebox 2 Moon Grey代表图，不代表全系列年度统计 | [g4/x08.jpg](g4/x08.jpg) | Toniebox 2 Moon Grey，非初代 | [tonies GmbH](https://tonies.com/en-eu/toniebox-2/) |
| [X11](../product-atlas.md#card-x11) · Microduck四配色官方主视觉 | [microduck/x11.jpg](microduck/x11.jpg) | 官方2026README，同一产品 | [Pollen Robotics](https://github.com/pollen-robotics/microduck/blob/main/README.md) |

## 更新与更正

原42项清单由四个冻结JSON数组顺序拼接，不统一裁掉不同组的扩展字段，也不以同product_id去重AIBI额外证据图。后续换图须保留来源／版本、更新SHA-256与尺寸并复核卡片；未明确授权前不修改parts或g*图文件。原40卡阶段仅整合现有素材；本轮按授权仅新增Microduck官方README主视觉900×312预览（46,696 bytes），已view_image核对，不增加视频。原38图／4视频及42条JSON对象字段不改；现39图共2,407,579 bytes，清单43项。来源访问失败、代际错配与未读内容详见U101—U113、U201—U210、U301—U317、U401—U418。
