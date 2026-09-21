# 作者肖像の出典

投稿アイコンには Wikimedia Commons の画像をローカル保存して使用する。以下はすべて各ファイルページで Public domain と表示されている版を採用した。

- 芥川龍之介: [Akutagawa Ryunosuke photo.jpg](https://commons.wikimedia.org/wiki/File:Akutagawa_Ryunosuke_photo.jpg)
- 石川啄木: [Takuboku Ishikawa.jpg](https://commons.wikimedia.org/wiki/File:Takuboku_Ishikawa.jpg)
- 尾崎放哉: [Ozaki Hosai 1.jpg](https://commons.wikimedia.org/wiki/File:Ozaki_Hosai_1.jpg)
- 種田山頭火: [Taneda Santoka, year unknown.jpg](https://commons.wikimedia.org/wiki/File:Taneda_Santoka,_year_unknown.jpg)
- 寺田寅彦: [Terada Torahiko in 1935.jpg](https://commons.wikimedia.org/wiki/File:Terada_Torahiko_in_1935.jpg)
- 正岡子規: [Masaoka Shiki.jpg](https://commons.wikimedia.org/wiki/File:Masaoka_Shiki.jpg)
- 北大路魯山人: [Rosanjin Kitaōji 1954.jpg](https://commons.wikimedia.org/wiki/File:Rosanjin_Kita%C5%8Dji_1954.jpg)
- 岡本かの子: [Kanoko Okamoto 01.jpg](https://commons.wikimedia.org/wiki/File:Kanoko_Okamoto_01.jpg)
- 高村光太郎: [Kotaro Takamura by Shigeru Tamura.jpg](https://commons.wikimedia.org/wiki/File:Kotaro_Takamura_by_Shigeru_Tamura.jpg)
- 下村湖人: [Kojin Shimomura mid-age.jpg](https://commons.wikimedia.org/wiki/File:Kojin_Shimomura_mid-age.jpg)
- 中島敦: [Nakajima Atsushi.jpg](https://commons.wikimedia.org/wiki/File:Nakajima_Atsushi.jpg)
- 中原中也: [Chuya1936.jpg](https://commons.wikimedia.org/wiki/File:Chuya1936.jpg)
- 萩原朔太郎: [Hagiwara Sakutaro.jpg](https://commons.wikimedia.org/wiki/File:Hagiwara_Sakutaro.jpg)
- 宮沢賢治: [Miyazawa Kenji.jpg](https://commons.wikimedia.org/wiki/File:Miyazawa_Kenji.jpg)
- 与謝野晶子: [YOSANO Akiko (cropped).jpg](https://commons.wikimedia.org/wiki/File:YOSANO_Akiko_(cropped).jpg)
- 北原白秋: [Kitahara Hakushu.jpg](https://commons.wikimedia.org/wiki/File:Kitahara_Hakushu.jpg)
- 八木重吉: [English teacher Jukichi Yagi.jpg](https://commons.wikimedia.org/wiki/File:English_teacher_Jukichi_Yagi.jpg)
- マルクス・アウレリウス: [Marcus Aurelius MET DP-615-004.jpg](https://commons.wikimedia.org/wiki/File:Marcus_Aurelius_MET_DP-615-004.jpg)
- フリードリヒ・ニーチェ: [Nietzsche1882.jpg](https://commons.wikimedia.org/wiki/File:Nietzsche1882.jpg)
- フランツ・カフカ: [Franz Kafka, 1923.jpg](https://commons.wikimedia.org/wiki/File:Franz_Kafka,_1923.jpg)
- エピクテトス: [Epictetus - Henri Bonnart engraving c. 1700.png](https://commons.wikimedia.org/wiki/File:Epictetus_-_Henri_Bonnart_engraving_c._1700.png)

権利を安全に確認できる肖像がない作者は、文字アイコンを使用する。

追加作者の肖像は `scripts/fetch_author_portraits.py` でWikidataの日本語Wikipedia対応項目が本人（human）であることを照合し、Wikimedia Commonsの `LicenseShortName` が Public domain / CC0 / PDM のものだけを取得する。作者ごとのWikidata ID、Commonsファイルページ、ライセンス、ローカルパスは `avatar_sources.json` に記録する。
