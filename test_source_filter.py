from test_support import client as protected_client
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
import bible_study_search_app as ui

class SourceFilterTests(unittest.TestCase):
    def rows(self):
        return [dict(title=f'Week {i}',path=f'/Reference/{name}/Week{i}.pdf',source_type='commentary',
                     passages=[dict(chunk_id=i,anchor='abc',snippet='worship '*20,books=[],evidence='')])
                for i,name in enumerate(['Other']*21+['52 Weeks of Pursuit'])]

    def test_filter_before_folding_and_keeps_reader_filter(self):
        with patch.object(ui.qbs,'run_query',return_value=self.rows()):
            response=protected_client(ui.app).get('/?q=worship&source_name=52+weeks+pursuit')
        self.assertEqual(response.status_code,200)
        soup=BeautifulSoup(response.data,'html.parser')
        self.assertIn('of 1 sources',soup.get_text())
        link=soup.find('a',string='Read this passage')['href']
        self.assertIn('source_name=52+weeks+pursuit',link)
        self.assertIn('52+Weeks',link)

    def test_counts_cover_later_pages_and_filter_paginates(self):
        rows=self.rows()
        for i,row in enumerate(rows):
            row['passages'][0]['snippet']=f'unique passage {i}'
        with patch.object(ui.qbs,'run_query',return_value=rows):
            response=protected_client(ui.app).get('/?q=worship&source_name=Reference&limit=10')
        soup=BeautifulSoup(response.data,'html.parser')
        self.assertIn('Commentaries: 22',soup.get_text(' ',strip=True))
        self.assertEqual(len(soup.find_all('a',string='Read this passage')),10)
        links=[a['href'] for a in soup.find_all('a',href=True) if 'page=2' in a['href']]
        self.assertTrue(links)
        self.assertTrue(all('source_name=Reference' in link for link in links))

if __name__=='__main__': unittest.main()
