# -*- coding: utf-8 -*-

#==============以下为修改后的版本思路================
# 新版代码url地址分析
# 主题思路，旧版本网站没有对获取的条数进行限制，
# 第一步根据每个分类的关键字获取搜索结果列表数据
# 从列表中获取旧版本的详情url地址，提取详情的id，新旧版网站的论文详情id是一样的，根据id拼接出新版网站的论文详情url地址
# 下面以期刊下的某一篇论文信息为例举例对比说明
# 旧版本的详情url地址
# http://d.old.wanfangdata.com.cn/Periodical/hbshkx201703005
# 新版本的详情URL地址
# http://www.wanfangdata.com.cn/details/detail.do?_type=perio&id=hbshkx201703005

import scrapy
from scrapy_redis.spiders import RedisSpider
import re
from urllib import parse
from wanfang.items import WanfangTechItem,WanfangDegreeItem,WanfangConferenceItem,WanfangPerioItem

class WflunwenSpider(RedisSpider):
    name = 'wflunwen'
    allowed_domains = ['wanfangdata.com.cn']
    # start_urls = [
    #     #政治
    #     'http://s.wanfangdata.com.cn/Paper.aspx?q=%e6%94%bf%e6%b2%bb+DBID%3aWF_QK&f=top&p=1',
    #     'http://s.wanfangdata.com.cn/Paper.aspx?q=%e6%94%bf%e6%b2%bb+DBID%3aWF_XW&f=top&p=1',
    #     'http://s.wanfangdata.com.cn/Paper.aspx?q=%e6%94%bf%e6%b2%bb+DBID%3aWF_HY&f=top&p=1',
    #     #法律
    #     'http://s.wanfangdata.com.cn/Paper.aspx?q=%e6%b3%95%e5%be%8b+DBID%3aWF_QK&f=top&p=1',
    #     'http://s.wanfangdata.com.cn/Paper.aspx?q=%e6%b3%95%e5%be%8b+DBID%3aWF_XW&f=top&p=1',
    #     'http://s.wanfangdata.com.cn/Paper.aspx?q=%e6%b3%95%e5%be%8b+DBID%3aWF_HY&f=top&p=1',
    # ]

    redis_key = 'wflunwen:start_urls'

    def parse(self, response):
        """
        从旧网站中获取获取每一个分类的（政治、法律）关键字的搜索结果
        :param response:
        :return:
        """
        print('请求成功',response.url)

        #论文标题列表
        #使用正则获取当前分类关键字和当前的页码数
        pattern = re.compile('.*?q=(.*?)\+.*?WF_(.*?)&.*?p=(\d+)',re.S)
        result = re.findall(pattern,response.url)[0]
        print(result)
        keyword = parse.unquote(result[0])
        tag = result[1]
        currentPage = result[2]
        #record-item-list
        itemList = response.xpath('//div[@class="record-item-list"]/div[@class="record-item"]')
        print(tag,keyword,'第',currentPage,'页，','获取到了',len(itemList),'条数据。')
        if len(itemList) > 0:
            for item in itemList:
                itemTitle = ''.join(item.xpath('.//a[@class="title"]//text()').extract()).replace(' ','')
                itemUrl = item.xpath('.//a[@class="title"]/@href').extract_first('')
                itemId = itemUrl.split('/')[-1:][0]
                if tag == 'HY':
                    #会议的详情
                    #http://www.wanfangdata.com.cn/details/detail.do?_type=conference&id=7730508
                    # print(itemTitle, itemUrl, '会议的详情',itemId)
                    newItemUrl = 'http://www.wanfangdata.com.cn/details/detail.do?_type=conference&id='+itemId
                    info = {
                        'searchKeyWord':keyword,
                        'searchType':'conference',
                    }
                    yield scrapy.Request(url=newItemUrl,callback=self.parse_detail_data,meta={'info':info,'title':itemTitle})

                elif tag == "XW":
                    #学位的详情
                    #http://www.wanfangdata.com.cn/details/detail.do?_type=degree&id=D01551993
                    # print(itemTitle, itemUrl, '学位的详情',itemId)
                    newItemUrl = 'http://www.wanfangdata.com.cn/details/detail.do?_type=degree&id=' + itemId
                    info = {
                        'searchKeyWord': keyword,
                        'searchType': 'degree',
                    }
                    yield scrapy.Request(url=newItemUrl, callback=self.parse_detail_data, meta={'info': info,'title':itemTitle})

                elif tag == "QK":
                    #期刊的详情
                    #http://www.wanfangdata.com.cn/details/detail.do?_type=perio&id=bjgydxxb-shkx201902004
                    # print(itemTitle, itemUrl, '期刊的详情', itemId)
                    newItemUrl = 'http://www.wanfangdata.com.cn/details/detail.do?_type=perio&id=' + itemId
                    info = {
                        'searchKeyWord': keyword,
                        'searchType': 'perio',
                    }

                    yield scrapy.Request(url=newItemUrl, callback=self.parse_detail_data, meta={'info': info,'title':itemTitle})

        #获取下一页
        nextUrls = response.xpath('//p[@class="pager"]//a[@class="page"]/@href').extract()
        if len(nextUrls):
            for nextUrl in nextUrls:
                nextUrl = response.urljoin(nextUrl)
                print(nextUrl)
                yield scrapy.Request(url=nextUrl,callback=self.parse)

    def parse_detail_data(self, response):

        info = response.meta['info']
        title = response.meta['title']
        print('详情请求状态码', title, info, response.status)
        if info['searchType'] == 'degree':
            print('正在获取学位分类论文信息')
            item = self.parse_degree(response, info)
            yield item
        elif info['searchType'] == 'perio':
            print('正在获取期刊分类论文信息')
            item = self.parse_perio(response, info)
            yield item
        elif info['searchType'] == 'conference':
            print('正在获取会议分类论文信息')
            item = self.parse_conference(response, info)
            yield item
        elif info['searchType'] == 'tech':
            print('正在获取科技报告分类论文信息')
            item = self.parse_tech(response, info)
            yield item

    def parse_degree(self, response, info):
        item = WanfangDegreeItem()
        item['url'] = response.url
        # title(中文标题)
        item['title'] = ''.join(response.xpath('//div[@class="title"]/text()').extract()).replace('\r\n', '').replace(
            '\t', '').replace('目录', '').replace(' ', '')

        # content(摘要)
        # item['content'] = ''.join(response.xpath('//input[@class="share_summary"]/@value').extract()).replace('\t',
        #                                                                                                       '').replace(
        #     ' ', '').replace('\r\n', '')
        item['content'] = ''.join(response.xpath('//div[@class="abstract"]/textarea/text()').extract()).replace('\u3000','').replace('\t','').replace(' ', '').replace('\n','')

        lis = response.xpath('//ul[@class="info"]//li')
        print(len(lis))
        for li in lis:
            if li.xpath('./div[@class="info_left"]/text()').extract_first('') == "关键词：":
                # keywords(关键词)
                item['keywords'] = '、'.join(li.xpath('.//a/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者：":
                # authors(作者)
                item['authors'] = li.xpath('.//a[1]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "学位授予单位：":
                # 学位授权单位
                item['degreeUnit'] = li.xpath('.//a[1]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "授予学位：":
                # 授予学位
                item['awardedTheDegree'] = li.xpath('./div[@class="info_right author"]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "学科专业：":
                # 学科专业
                item['professional'] = li.xpath('.//a[1]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "导师姓名：":
                # 导师姓名
                item['mentorName'] = li.xpath('.//a[1]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "学位年度：":
                # 学位年度
                item['degreeInAnnual'] = li.xpath('./div[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "语种：":
                # 语种
                item['languages'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n','').replace('\t', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "分类号：":
                # 分类号
                item['classNumber'] = ' '.join(li.xpath('./div[2]//text()').extract()).replace('\r\n',' ').replace('\t', '').strip(' ')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "在线出版日期：":
                # 在线出版日期
                item['publishTime'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n', '').replace('\t', '').replace(' ', '')

        item['searchKey'] = info['searchKeyWord']
        item['searchType'] = info['searchType']

        return item

    def parse_perio(self, response, info):
        item = WanfangPerioItem()
        item['url'] = response.url
        # title(中文标题)
        item['title'] = response.xpath('//div[@class="title"]/text()').extract_first('').replace('\r\n', '').replace(
            ' ', '').replace('\t', '')
        # englishTitle(英文标题)
        item['englishTitle'] = response.xpath('//div[@class="English"]/text()').extract_first('暂无').replace('\t', '')
        # content(摘要)
        # item['content'] = ''.join(response.xpath('//input[@class="share_summary"]/@value').extract()).replace('\t',
        #                                                                                                      '').replace(
        #     ' ', '').replace('\r\n', '')
        item['content'] = ''.join(response.xpath('//div[@class="abstract"]/textarea/text()').extract()).replace('\u3000','').replace('\t','').replace(' ', '').replace('\n','')

        lis = response.xpath('//ul[@class="info"]//li')
        print(len(lis))
        for li in lis:
            # print(li.xpath('./div[@class="info_left"]/text()').extract_first(''))
            if li.xpath('./div[@class="info_left"]/text()').extract_first('') == "doi：":
                item['doi'] = li.xpath('.//a/text()').extract_first('').replace('\t', '').replace(' ', '')
            elif li.xpath('./div[@class="info_left "]/text()').extract_first('') == "关键词：":
                # keywords(关键词)
                item['keywords'] = '、'.join(li.xpath('.//a/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "Keyword：":
                item['englishKeyWords'] = '、'.join(li.xpath('.//a/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者：":
                item['authors'] = '、'.join(li.xpath('./div[@class="info_right"]/a[@class="info_right_name"]/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "Author：":
                item['englishAuthors'] = '、'.join(li.xpath('./div[@class="info_right"]/a[@class="info_right_name"]/text()').extract()).replace('\n', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者单位：":
                item['unit'] = '、'.join(li.xpath('.//a/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "刊名：":
                item['journalName'] = li.xpath('.//a[@class="college"]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "Journal：":
                item['journal'] = li.xpath('.//a[1]/text()').extract_first('')
                if len(item['journal']) == 0:
                    item['journal'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r\n', '').replace(' ',
                                                                                                                 '').replace(
                    '\t', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "年，卷(期)：":
                item['yearsInfo'] = li.xpath('.//a/text()').extract_first('')
                if len(item['yearsInfo']) == 0:
                    item['yearsInfo'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r\n', '').replace(' ',
                                                                                                                 '').replace(
                    '\t', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "所属期刊栏目：":
                item['journalSection'] = li.xpath('.//a/text()').extract_first('')
                if len(item['journalSection']) == 0:
                    item['journalSection'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r\n', '').replace(' ',
                                                                                                                 '').replace(
                    '\t', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "分类号：":
                item['classNumber'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r', '').replace('\n',
                                                                                                               '').replace(
                    '\t', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "基金项目：":
                item['fundProgram'] = li.xpath('.//a[1]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "在线出版日期：":
                item['publishTime'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r\n', '').replace(' ',
                                                                                                                 '').replace(
                    '\t', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "页数：":
                item['pages'] = li.xpath('.//div[2]/text()').extract_first('').replace(' ','')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "页码：":
                item['pageNumber'] = li.xpath('.//div[2]/text()').extract_first('').replace(' ','')

        item['searchKey'] = info['searchKeyWord']
        item['searchType'] = info['searchType']
        return item

    def parse_conference(self, response, info):

        item = WanfangConferenceItem()
        item['url'] = response.url
        # title(中文标题)
        item['title'] = ''.join(response.xpath('//div[@class="title"]/text()').extract()).replace('\r\n', '').replace(
            '\t', '').replace('目录', '').replace(' ', '')
        # content(摘要)
        # item['content'] = ''.join(response.xpath('//input[@class="share_summary"]/@value').extract()).replace('\t','').replace(' ', '').replace('\r\n', '').replace('\u3000', '')
        item['content'] = ''.join(response.xpath('//div[@class="abstract"]/textarea/text()').extract()).replace('\u3000','').replace('\t','').replace(' ', '').replace('\n','')

        lis = response.xpath('//ul[@class="info"]//li')
        print(len(lis))
        for li in lis:
            if li.xpath('./div[@class="info_left"]/text()').extract_first('') == "关键词：":
                # keywords(关键词)
                item['keywords'] = '、'.join(li.xpath('.//a/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者：":
                # authors(作者)
                item['authors'] = '、'.join(li.xpath('.//a/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者单位：":
                # 作者单位
                item['unit'] = '、'.join(li.xpath('.//a[1]/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "母体文献：":
                # 母体文献
                item['literature'] = li.xpath('./div[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "会议名称：":
                # 会议名称
                item['meetingName'] = li.xpath('./div[2]/a[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "会议时间：":
                # 会议时间
                item['meetingTime'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n', '').replace('\t',
                                                                                                                '').replace(
                    ' ', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "会议地点：":
                # 会议地点
                item['meetingAdress'] = li.xpath('./div[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "主办单位：":
                # 主办单位
                item['organizer'] = '、'.join(li.xpath('./div[2]//a/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "语 种：":
                # 语种
                item['languages'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n', '').replace('\t', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "分类号：":
                # 分类号
                item['classNumber'] = ''.join(li.xpath('./div[2]/text()').extract()).replace('\r\n', '').replace('\t',
                                                                                                                 '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "在线出版日期：":
                # 发布时间
                item['publishTime'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n', '').replace('\t',
                                                                                                                '').replace(
                    ' ', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "页码：":
                # 页码
                item['pageNumber'] = li.xpath('./div[2]/text()').extract_first('')

        item['searchKey'] = info['searchKeyWord']
        item['searchType'] = info['searchType']
        return item

    def parse_tech(self, response, info):

        item = WanfangTechItem()
        item['url'] = response.url
        # title(中文标题)
        item['title'] = response.xpath('//div[@class="title"]/text()').extract_first('').replace('\r\n', '').replace(
            ' ', '').replace('\t', '')
        # englishTitle(英文标题)
        item['englishTitle'] = response.xpath('//div[@class="English"]/text()').extract_first('暂无').replace('\t', '')
        # content(摘要)
        # item['content'] = ''.join(response.xpath('//input[@class="share_summary"]/@value').extract()).replace('\t',
        #                                                                                                       '').replace(
        #     ' ', '').replace('\r\n', '')
        item['content'] = ''.join(response.xpath('//div[@class="abstract"]/textarea/text()').extract()).replace('\u3000','').replace('\t','').replace(' ', '').replace('\n','')

        lis = response.xpath('//ul[@class="info"]//li')
        print(len(lis))
        for li in lis:
            if li.xpath('./div[@class="info_left"]/text()').extract_first('') == "关键词：":
                # keywords(关键词)
                item['keywords'] = '、'.join(li.xpath('.//a/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者：":
                # authors(作者)
                item['authors'] = '、'.join(li.xpath('.//a/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者单位：":
                # 作者单位
                item['unit'] = '、'.join(li.xpath('.//a[1]/text()').extract())
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "报告类型：":
                # 报告类型
                item['reportType'] = li.xpath('./div[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "公开范围：":
                # 公开范围
                item['openRange'] = li.xpath('./div[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "全文页数：":
                # 全文页数
                item['pageNumber'] = li.xpath('./div[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "项目/课题名称：":
                # 项目/课题名称
                item['projectName'] = li.xpath('./div[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "计划名称：":
                # 计划名称
                item['planName'] = li.xpath('./div[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "编制时间：":
                # 编制时间
                item['compileTime'] = li.xpath('./div[2]/text()').extract_first('').replace('\t', '').replace(' ',
                                                                                                              '').replace(
                    '\r\n', '')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "立项批准年：":
                # 立项批准年
                item['approvalYear'] = li.xpath('./div[2]/text()').extract_first('')
            elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "馆藏号：":
                # 馆藏号
                item['collection'] = li.xpath('./div[2]/text()').extract_first('')

        item['searchKey'] = info['searchKeyWord']
        item['searchType'] = info['searchType']
        return item

#以下为之前的版本
# import scrapy
# from wanfang.items import WanfangPerioItem,WanfangDegreeItem,WanfangConferenceItem,WanfangTechItem
# import re
# from urllib import parse
# import json
# from scrapy_redis.spiders import RedisSpider
#
#
# # class WflunwenSpider(scrapy.Spider):
# class WflunwenSpider(RedisSpider):
#     name = 'wflunwen'
#     allowed_domains = ['wanfangdata.com.cn']
#     """
#     http://g.wanfangdata.com.cn/search/searchList.do?searchType=perio&showType=&pageSize=&searchWord=%E6%B3%95%E5%BE%8B&isTriggerTag=
#     http://g.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=perio&pageSize=20&page=2&searchWord=%E6%B3%95%E5%BE%8B&order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=perio
#     """
#     # start_urls = [
#     #     'http://www.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=degree&pageSize=50&page=1&searchWord=%E6%B3%95%E5%BE%8B&order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=degree',
#     #     'http://www.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=degree&pageSize=50&page=1&searchWord=%E6%94%BF%E6%B2%BB&order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=degree',
#     #     'http://www.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=perio&pageSize=50&page=1&searchWord=%E6%94%BF%E6%B2%BB&order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=perio',
#     #     'http://www.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=perio&pageSize=50&page=1&searchWord=%E6%B3%95%E5%BE%8B&order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=perio',
#     #     'http://www.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=conference&pageSize=50&page=1&searchWord=%E6%B3%95%E5%BE%8B&order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=conference',
#     #     'http://www.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=conference&pageSize=50&page=1&searchWord=%E6%94%BF%E6%B2%BB&order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=conference',
#     #     'http://www.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=tech&pageSize=50&page=1&searchWord=%E6%B3%95%E5%BE%8B&order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=tech',
#     #     'http://www.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=tech&pageSize=50&page=1&searchWord=%E6%94%BF%E6%B2%BB&order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=tech',
#     # ]
#     redis_key = 'wflunwen:start_urls'
#
#     def parse(self, response):
#         # 获取当前请求搜索的关键字
#         pattern = re.compile('.*?searchWord=(.*?)&', re.S)
#         searchKeyWord = re.findall(pattern, response.url)[0]
#         searchKeyWord = parse.unquote(searchKeyWord)
#         # 获取当前请求搜素的分类
#         pattern = re.compile('.*?searchType=(.*?)&', re.S)
#         searchType = re.findall(pattern, response.url)[0]
#
#         totalRow = int(response.xpath('.//input[@id="totalRow"]/@value').extract_first(''))
#
#         if totalRow > 5000:
#             #获取到的第一页数据总数量大于5000的时候
#             """
#             searchType: degree
#             searchWord: (%E6%94%BF%E6%B2%BB)（政治）
#             facetField:
#             isHit:
#             startYear:
#             endYear:
#             offset: 0
#             limit: 6
#             hqfwfacetField:
#             navSearchType:
#             """
#             print(searchKeyWord, searchType, '数据量', totalRow,'大于5000')
#             form_data = {
#                 'searchType': searchType,
#                 'searchWord': '('+parse.quote(searchKeyWord)+')',
#                 'facetField':'',
#                 'isHit':'',
#                 'startYear':'',
#                 'endYear':'',
#                 'offset': '0',
#                 'limit': '10',
#                 'hqfwfacetField':'',
#                 'navSearchType':'',
#             }
#
#             yield scrapy.FormRequest(url='http://g.wanfangdata.com.cn/search/navigation.do',formdata=form_data,
#                                      callback=self.parse_navigation_data,meta={'baseUrl':response.url,'searchType':form_data['searchType'],'searchKeyWord':searchKeyWord,'total':'YES'},
#                                      dont_filter=True
#                                      )
#             yield scrapy.Request(url=response.url, callback=self.parse_pagelist_data, dont_filter=True)
#
#             headers={
#                 # 'Referer': 'http://www.wanfangdata.com.cn/search/searchList.do?searchType=conference&showType=&pageSize=&searchWord=%E6%B3%95%E5%BE%8B&isTriggerTag=',
#                 'Referer': 'http://www.wanfangdata.com.cn/search/searchList.do?searchType=%s&showType=&pageSize=&searchWord=%s&isTriggerTag=' % (searchType,parse.quote(searchKeyWord)),
#                 # "Referer": "http://www.wanfangdata.com.cn/search/searchList.do?searchType=conference&showType=&pageSize=&searchWord=%E6%B3%95%E5%BE%8B&isTriggerTag=",
#                 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36',
#             }
#
#             if searchType == 'conference':
#                 """
#                 #$common_year 会议 年份（法、政治）
#                 #$subject_classcode_level 会议 学科分类
#                 #$conf_type 会议 会议级别
#                 #$language 会议 语种
#                 #$source_db 会议 数据来源
#                 #$conf_name02 会议 会议名称
#                 ##$authors_name 会议 作者
#                 #$unit_name02 会议 机构
#                 #$hostunit_name02 会议 会议主办单位
#                 """
#                 category_data = [
#                     '$common_year','$subject_classcode_level','$conf_type',
#                     '$language','$source_db','$conf_name02','$authors_name',
#                     '$unit_name02','hostunit_name02'
#                 ]
#
#                 for category_name in category_data:
#                     form_data = self.get_category_request_formdata(searchType, searchKeyWord, category_name, '11')
#                     print(form_data)
#                     yield scrapy.FormRequest(url='http://www.wanfangdata.com.cn/search/navigation.do', formdata=form_data,
#                                              callback=self.parse_navigation_data,headers=headers,
#                                              meta={'baseUrl': response.url, 'searchType': form_data['searchType'],
#                                                    'searchKeyWord': searchKeyWord,'total':'NO','limit':'11','lastcount':'0'},
#                                              dont_filter=True
#                                              )
#             elif searchType == 'perio':
#                 """
#                 # $common_year 期刊 年份
#                 # $subject_classcode_level 期刊 学科分类
#                 # $core_perio 期刊 （核心）
#                 # $language 期刊 语种
#                 # $source_db 期刊 （来源数据库）
#                 # $perio_title02 期刊 （刊名）
#                 # $first_publish 期刊 （出版状态）
#                 # $unit_name02 期刊 （机构）
#                 # $authors_name 期刊 （作者）
#                 """
#                 category_data = [
#                     '$common_year','$subject_classcode_level','$core_perio',
#                     '$language','$source_db','$perio_title02','$first_publish',
#                     '$unit_name02','$authors_name',
#                 ]
#
#                 for category_name in category_data:
#                     form_data = self.get_category_request_formdata(searchType, searchKeyWord, category_name, '11')
#                     yield scrapy.FormRequest(url='http://www.wanfangdata.com.cn/search/navigation.do',
#                                              formdata=form_data,
#                                              callback=self.parse_navigation_data, headers=headers,
#                                              meta={'baseUrl': response.url, 'searchType': form_data['searchType'],
#                                                    'searchKeyWord': searchKeyWord, 'total': 'NO', 'limit': '11',
#                                                    'lastcount': '0'},
#                                              dont_filter=True
#                                              )
#             elif searchType == 'degree':
#                 """
#                 # $common_year 学位 年份
#                 # $subject_classcode_level 学位 学科分类
#                 # $degree_level 学位 授予学位
#                 # $language 学位 语种
#                 # $tutor_name 学位 导师
#                 # $unit_name02 学位（授予单位）
#                 """
#
#                 category_data = [
#                     '$common_year','$subject_classcode_level','$degree_level',
#                     '$language','$tutor_name','$unit_name02'
#                 ]
#
#                 for category_name in category_data:
#                     form_data = self.get_category_request_formdata(searchType,searchKeyWord,category_name,'11')
#                     yield scrapy.FormRequest(url='http://www.wanfangdata.com.cn/search/navigation.do',
#                                              formdata=form_data,
#                                              callback=self.parse_navigation_data, headers=headers,
#                                              meta={'baseUrl': response.url, 'searchType': form_data['searchType'],
#                                                    'searchKeyWord': searchKeyWord, 'total': 'NO', 'limit': '11',
#                                                    'lastcount': '0'},
#                                              dont_filter=True
#                                              )
#         else:
#             print(searchKeyWord, searchType, '数据量', totalRow, '小于5000')
#             yield scrapy.Request(url=response.url,callback=self.parse_pagelist_data,dont_filter=True)
#
#     def get_category_request_formdata(self,searchType,searchKeyWord,category_name,limit):
#
#         form_data = {
#             'searchType': searchType,
#             'searchWord': '(' + parse.quote(searchKeyWord) + ')',
#             'facetField': category_name,
#             'isHit': '',
#             'startYear': '',
#             'endYear': '',
#             'limit': limit,
#             'hqfwfacetField': '',
#             'navSearchType': '',
#             'single': 'true',
#             'bindFieldLimit': '{}',
#         }
#
#         return form_data
#
#
#     def parse_navigation_data(self,response):
#         if '万方数据知识服务平台' in response.text:
#             print('没有获取到分类数据')
#         else:
#             print('111111------------------------------')
#
#             data = json.loads(response.text)
#             base_url = response.meta['baseUrl']
#             searchType = response.meta['searchType']
#             searchKeyWord = response.meta['searchKeyWord']
#             total = response.meta['total']
#             if total == "NO":
#                 lastcount = int(response.meta['lastcount'])
#             else:
#                 lastcount = 0
#
#             print('导航栏数据获取成功',searchType,searchKeyWord)
#             for sub_dict in data['facetTree'][lastcount:]:
#                 if sub_dict['pId'] != '-1':
#                     # print(sub_dict)
#                     if sub_dict['facetField'] == '$subject_classcode_level': #学科分类
#                         # &facetField=$subject_classcode_level:%E2%88%B7/D&facetName=%E6%94%BF%E6%B2%BB%E3%80%81%E6%B3%95%E5%BE%8B:$subject_classcode_level
#                         # &facetField=$subject_classcode_level:∷/D&facetName=政治、法律:$subject_classcode_level
#                         full_url = base_url + '&facetField=%s&facetName=%s' % (sub_dict['facetField']+':'+'%E2%88%B7'+'/'+sub_dict['value'],parse.quote(sub_dict['showName'])+':'+sub_dict['facetField'])
#                         print(full_url)
#                         yield scrapy.Request(url=full_url, callback=self.parse_pagelist_data)
#
#                     elif sub_dict['facetField'] == '$language': #语种
#                         """
#                         &facetField=$language:chi&facetName=%E4%B8%AD%E6%96%87:$language
#                         &facetField=$language:chi&facetName=中文:$language
#                         """
#                         full_url = base_url + '&facetField=%s&facetName=%s' % (sub_dict['facetField']+':'+sub_dict['value'],parse.quote(sub_dict['showName'])+':'+sub_dict['facetField'])
#                         print(full_url)
#                         yield scrapy.Request(url=full_url, callback=self.parse_pagelist_data)
#
#                     else:
#                         #其他的都是一样的格式
#                         """
#                         &facetField=$tutor_name:%E8%83%A1%E9%B8%BF%E9%AB%98&facetName=%E8%83%A1%E9%B8%BF%E9%AB%98:$tutor_name
#                         &facetField=$tutor_name:胡鸿高&facetName=胡鸿高:$tutor_name
#                         """
#                         full_url = base_url + '&facetField=%s&facetName=%s' % (sub_dict['facetField']+':'+parse.quote(sub_dict['value']),parse.quote(sub_dict['showName'])+':'+sub_dict['facetField'])
#                         print(full_url)
#                         yield scrapy.Request(url=full_url, callback=self.parse_pagelist_data)
#
#
#             if total == 'NO':
#                 limit = int(response.meta['limit'])
#                 print(limit,lastcount+1,len(data['facetTree']))
#                 #如果没有获取完毕分类数据，继续获取
#                 if len(data['facetTree']) == lastcount+1:
#                     print('分类加载完毕')
#                 else:
#                     # 还没有获取完毕，继续获取
#                     form_data = self.get_category_request_formdata(searchType, searchKeyWord,
#                                                                    sub_dict['facetField'], str(limit + 5))
#                     lastcount = str(len(data['facetTree']) - 1)
#                     yield scrapy.FormRequest(url='http://www.wanfangdata.com.cn/search/navigation.do',
#                                              formdata=form_data,
#                                              callback=self.parse_navigation_data,
#                                              meta={'baseUrl': base_url,
#                                                    'searchType': form_data['searchType'],
#                                                    'searchKeyWord': searchKeyWord, 'total': 'NO',
#                                                    'limit': str(limit + 5),
#                                                    'lastcount': lastcount},
#                                              dont_filter=True
#                                              )
#
#     def parse_pagelist_data(self,response):
#
#         print('列表数据请求的状态码:', response.status)
#         # 获取论文列表
#         #thesis = response.xpath('//div[@class="ResultList"]/div[@class="ResultCont"]/div[@class="title"]')
#         thesis = response.xpath('//div[contains(@class,"ResultList")]/div[@class="ResultCont"]/div[@class="title"]')
#
#         headers = {
#             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
#             "Referer": response.url,
#         }
#         # 获取当前请求搜索的关键字
#         pattern = re.compile('.*?searchWord=(.*?)&', re.S)
#         searchKeyWord = re.findall(pattern, response.url)[0]
#         searchKeyWord = parse.unquote(searchKeyWord)
#         # 获取当前请求搜素的分类
#         pattern = re.compile('.*?searchType=(.*?)&', re.S)
#         searchType = re.findall(pattern, response.url)[0]
#         print(searchKeyWord, searchType)
#
#         info = {
#             'searchKeyWord': searchKeyWord,
#             'searchType': searchType,
#         }
#
#         if len(thesis) > 0:
#             print('获取到了' + str(len(thesis)) + '条数据', info)
#             # 便利循环论文列表获取详情链接
#             for article in thesis:
#                 # print(article)
#                 title = ''.join(article.xpath('./a[1]//text()').extract())
#                 # http://www.wanfangdata.com.cn/details/detail.do?_type=standards&id=T/OVMA%20024-2018
#                 detail_url = response.urljoin(article.xpath('./a[1]/@href').extract_first(''))
#                 if '目录' in title.replace(' ', '') and 'javascript:void(0)' in detail_url:
#                     title = ''.join(article.xpath('./a[2]//text()').extract())
#                     detail_url = response.urljoin(article.xpath('./a[2]/@href').extract_first(''))
#                 yield scrapy.Request(url=detail_url, headers=headers, callback=self.parse_detail_data,
#                                      meta={'info': info, 'title': title})
#
#             # 提取下一页分页地址
#             cur_page_num = int(response.xpath('.//input[@id="pageNum"]/@value').extract_first(''))
#             pageTotal = int(response.xpath('.//input[@id="pageTotal"]/@value').extract_first(''))
#             if cur_page_num <= pageTotal:
#                 next_page_num = cur_page_num + 1
#                 pattern = re.compile('page=\d+', re.S)
#                 next_url = re.sub(pattern, 'page=' + str(next_page_num), response.url)
#                 print('第' + str(next_page_num) + '页', next_url)
#
#                 """
#                 对比分页的链接，寻找规律
#                 http://g.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=perio&pageSize=20&page=4&searchWord=%E6%B3%95%E5%BE%8B
#                 &order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=perio
#
#                 http://g.wanfangdata.com.cn/search/searchList.do?beetlansyId=aysnsearch&searchType=perio&pageSize=20&page=2&searchWord=%E6%B3%95%E5%BE%8B
#                 &order=correlation&showType=detail&isCheck=check&isHit=&isHitUnit=&firstAuthor=false&rangeParame=&navSearchType=perio
#                 """
#                 yield scrapy.Request(url=next_url, headers=headers, callback=self.parse_pagelist_data)
#             else:
#                 print(info, '分页数据加载完毕')
#         else:
#             print('当前页面获取数据失败')
#             print(response.url)
#
#
#     def parse_detail_data(self, response):
#
#         info = response.meta['info']
#         print('详情请求状态码', response.meta['title'], info, response.status,)
#         if info['searchType'] == 'degree':
#             print('正在获取学位分类论文信息')
#             item = self.parse_degree(response, info)
#             yield item
#         elif info['searchType'] == 'perio':
#             print('正在获取期刊分类论文信息')
#             item = self.parse_perio(response, info)
#             yield item
#         elif info['searchType'] == 'conference':
#             print('正在获取会议分类论文信息')
#             item = self.parse_conference(response, info)
#             yield item
#         elif info['searchType'] == 'tech':
#             print('正在获取科技报告分类论文信息')
#             item = self.parse_tech(response, info)
#             yield item
#
#     def parse_degree(self, response, info):
#         item = WanfangDegreeItem()
#         item['url'] = response.url
#         # title(中文标题)
#         item['title'] = ''.join(response.xpath('//div[@class="title"]/text()').extract()).replace('\r\n', '').replace(
#             '\t', '').replace('目录', '').replace(' ', '')
#
#         # content(摘要)
#         # item['content'] = ''.join(response.xpath('//input[@class="share_summary"]/@value').extract()).replace('\t',
#         #                                                                                                       '').replace(
#         #     ' ', '').replace('\r\n', '')
#         item['content'] = ''.join(response.xpath('//div[@class="abstract"]/textarea/text()').extract())
#
#         lis = response.xpath('//ul[@class="info"]//li')
#         print(len(lis))
#         for li in lis:
#             if li.xpath('./div[@class="info_left"]/text()').extract_first('') == "关键词：":
#                 # keywords(关键词)
#                 item['keywords'] = '、'.join(li.xpath('.//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者：":
#                 # authors(作者)
#                 item['authors'] = li.xpath('.//a[1]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "学位授予单位：":
#                 # 学位授权单位
#                 item['degreeUnit'] = li.xpath('.//a[1]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "授予学位：":
#                 # 授予学位
#                 item['awardedTheDegree'] = li.xpath('./div[@class="info_right author"]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "学科专业：":
#                 # 学科专业
#                 item['professional'] = li.xpath('.//a[1]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "导师姓名：":
#                 # 导师姓名
#                 item['mentorName'] = li.xpath('.//a[1]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "学位年度：":
#                 # 学位年度
#                 item['degreeInAnnual'] = li.xpath('./div[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "语种：":
#                 # 语种
#                 item['languages'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n','').replace('\t', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "分类号：":
#                 # 分类号
#                 item['classNumber'] = ' '.join(li.xpath('./div[2]//text()').extract()).replace('\r\n',' ').replace('\t', '').strip(' ')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "在线出版日期：":
#                 # 在线出版日期
#                 item['publishTime'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n', '').replace('\t', '').replace(' ', '')
#
#         item['searchKey'] = info['searchKeyWord']
#         item['searchType'] = info['searchType']
#
#         return item
#
#     def parse_perio(self, response, info):
#         item = WanfangPerioItem()
#         item['url'] = response.url
#         # title(中文标题)
#         item['title'] = response.xpath('//div[@class="title"]/text()').extract_first('').replace('\r\n', '').replace(
#             ' ', '').replace('\t', '')
#         # englishTitle(英文标题)
#         item['englishTitle'] = response.xpath('//div[@class="English"]/text()').extract_first('暂无').replace('\t', '')
#         # content(摘要)
#         # item['content'] = ''.join(response.xpath('//input[@class="share_summary"]/@value').extract()).replace('\t',
#         #                                                                                                      '').replace(
#         #     ' ', '').replace('\r\n', '')
#         item['content'] = ''.join(response.xpath('//div[@class="abstract"]/textarea/text()').extract())
#
#         lis = response.xpath('//ul[@class="info"]//li')
#         print(len(lis))
#         for li in lis:
#             # print(li.xpath('./div[@class="info_left"]/text()').extract_first(''))
#             if li.xpath('./div[@class="info_left"]/text()').extract_first('') == "doi：":
#                 item['doi'] = li.xpath('.//a/text()').extract_first('').replace('\t', '').replace(' ', '')
#             elif li.xpath('./div[@class="info_left "]/text()').extract_first('') == "关键词：":
#                 # keywords(关键词)
#                 item['keywords'] = '、'.join(li.xpath('.//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "Keyword：":
#                 item['englishKeyWords'] = '、'.join(li.xpath('.//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者：":
#                 item['authors'] = '、'.join(li.xpath('.//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "Author：":
#                 item['englishAuthors'] = '、'.join(li.xpath('.//a/text()').extract()).replace('\n', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者单位：":
#                 item['unit'] = '、'.join(li.xpath('.//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "刊名：":
#                 item['journalName'] = li.xpath('.//a[@class="college"]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "Journal：":
#                 item['journal'] = li.xpath('.//a[1]/text()').extract_first('')
#                 if len(item['journal']) == 0:
#                     item['journal'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r\n', '').replace(' ',
#                                                                                                                  '').replace(
#                     '\t', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "年，卷(期)：":
#                 item['yearsInfo'] = li.xpath('.//a/text()').extract_first('')
#                 if len(item['yearsInfo']) == 0:
#                     item['yearsInfo'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r\n', '').replace(' ',
#                                                                                                                  '').replace(
#                     '\t', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "所属期刊栏目：":
#                 item['journalSection'] = li.xpath('.//a/text()').extract_first('')
#                 if len(item['journalSection']) == 0:
#                     item['journalSection'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r\n', '').replace(' ',
#                                                                                                                  '').replace(
#                     '\t', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "分类号：":
#                 item['classNumber'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r', '').replace('\n',
#                                                                                                                '').replace(
#                     '\t', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "基金项目：":
#                 item['fundProgram'] = li.xpath('.//a[1]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "在线出版日期：":
#                 item['publishTime'] = li.xpath('.//div[2]/text()').extract_first('').replace('\r\n', '').replace(' ',
#                                                                                                                  '').replace(
#                     '\t', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "页数：":
#                 item['pages'] = li.xpath('.//div[2]/text()').extract_first('').replace(' ','')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "页码：":
#                 item['pageNumber'] = li.xpath('.//div[2]/text()').extract_first('').replace(' ','')
#
#         item['searchKey'] = info['searchKeyWord']
#         item['searchType'] = info['searchType']
#         return item
#
#     def parse_conference(self, response, info):
#
#         item = WanfangConferenceItem()
#         item['url'] = response.url
#         # title(中文标题)
#         item['title'] = ''.join(response.xpath('//div[@class="title"]/text()').extract()).replace('\r\n', '').replace(
#             '\t', '').replace('目录', '').replace(' ', '')
#         # content(摘要)
#         # item['content'] = ''.join(response.xpath('//input[@class="share_summary"]/@value').extract()).replace('\t','').replace(' ', '').replace('\r\n', '').replace('\u3000', '')
#         item['content'] = ''.join(response.xpath('//div[@class="abstract"]/textarea/text()').extract())
#
#         lis = response.xpath('//ul[@class="info"]//li')
#         print(len(lis))
#         for li in lis:
#             if li.xpath('./div[@class="info_left"]/text()').extract_first('') == "关键词：":
#                 # keywords(关键词)
#                 item['keywords'] = '、'.join(li.xpath('.//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者：":
#                 # authors(作者)
#                 item['authors'] = '、'.join(li.xpath('.//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者单位：":
#                 # 作者单位
#                 item['unit'] = '、'.join(li.xpath('.//a[1]/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "母体文献：":
#                 # 母体文献
#                 item['literature'] = li.xpath('./div[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "会议名称：":
#                 # 会议名称
#                 item['meetingName'] = li.xpath('./div[2]/a[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "会议时间：":
#                 # 会议时间
#                 item['meetingTime'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n', '').replace('\t',
#                                                                                                                 '').replace(
#                     ' ', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "会议地点：":
#                 # 会议地点
#                 item['meetingAdress'] = li.xpath('./div[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "主办单位：":
#                 # 主办单位
#                 item['organizer'] = '、'.join(li.xpath('./div[2]//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "语 种：":
#                 # 语种
#                 item['languages'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n', '').replace('\t', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "分类号：":
#                 # 分类号
#                 item['classNumber'] = ''.join(li.xpath('./div[2]/text()').extract()).replace('\r\n', '').replace('\t',
#                                                                                                                  '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "在线出版日期：":
#                 # 发布时间
#                 item['publishTime'] = li.xpath('./div[2]/text()').extract_first('').replace('\r\n', '').replace('\t',
#                                                                                                                 '').replace(
#                     ' ', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "页码：":
#                 # 页码
#                 item['pageNumber'] = li.xpath('./div[2]/text()').extract_first('')
#
#         item['searchKey'] = info['searchKeyWord']
#         item['searchType'] = info['searchType']
#         return item
#
#     def parse_tech(self, response, info):
#
#         item = WanfangTechItem()
#         item['url'] = response.url
#         # title(中文标题)
#         item['title'] = response.xpath('//div[@class="title"]/text()').extract_first('').replace('\r\n', '').replace(
#             ' ', '').replace('\t', '')
#         # englishTitle(英文标题)
#         item['englishTitle'] = response.xpath('//div[@class="English"]/text()').extract_first('暂无').replace('\t', '')
#         # content(摘要)
#         # item['content'] = ''.join(response.xpath('//input[@class="share_summary"]/@value').extract()).replace('\t',
#         #                                                                                                       '').replace(
#         #     ' ', '').replace('\r\n', '')
#         item['content'] = ''.join(response.xpath('//div[@class="abstract"]/textarea/text()').extract())
#
#         lis = response.xpath('//ul[@class="info"]//li')
#         print(len(lis))
#         for li in lis:
#             if li.xpath('./div[@class="info_left"]/text()').extract_first('') == "关键词：":
#                 # keywords(关键词)
#                 item['keywords'] = '、'.join(li.xpath('.//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者：":
#                 # authors(作者)
#                 item['authors'] = '、'.join(li.xpath('.//a/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "作者单位：":
#                 # 作者单位
#                 item['unit'] = '、'.join(li.xpath('.//a[1]/text()').extract())
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "报告类型：":
#                 # 报告类型
#                 item['reportType'] = li.xpath('./div[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "公开范围：":
#                 # 公开范围
#                 item['openRange'] = li.xpath('./div[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "全文页数：":
#                 # 全文页数
#                 item['pageNumber'] = li.xpath('./div[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "项目/课题名称：":
#                 # 项目/课题名称
#                 item['projectName'] = li.xpath('./div[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "计划名称：":
#                 # 计划名称
#                 item['planName'] = li.xpath('./div[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "编制时间：":
#                 # 编制时间
#                 item['compileTime'] = li.xpath('./div[2]/text()').extract_first('').replace('\t', '').replace(' ',
#                                                                                                               '').replace(
#                     '\r\n', '')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "立项批准年：":
#                 # 立项批准年
#                 item['approvalYear'] = li.xpath('./div[2]/text()').extract_first('')
#             elif li.xpath('./div[@class="info_left"]/text()').extract_first('') == "馆藏号：":
#                 # 馆藏号
#                 item['collection'] = li.xpath('./div[2]/text()').extract_first('')
#
#         item['searchKey'] = info['searchKeyWord']
#         item['searchType'] = info['searchType']
#         return item
#
#
#
