import unittest
from predash.watch_compare import comparison_rows, comparison_warnings, comparison_csv


class WatchComparisonTests(unittest.TestCase):
    def test_partial_failure_keeps_all_codes_and_zero(self):
        metrics={'year':2026,'quarter':2,'basis':'CFS','revenue':100,'profit':0,
                 'growth_pct':None,'revenue_growth_pct':0,'margin_pct':0}
        rows=comparison_rows(['005930','000660'],{'005930':{'metrics':metrics,
            'krx':{'market_cap':1000000000}}},{'000660':'SK하이닉스'})
        self.assertEqual(rows[0]['시가총액 (억원)'],10)
        self.assertEqual(rows[0]['영업이익 (억원)'],0)
        self.assertIsNone(rows[0]['영업이익 증가율 (%)'])
        self.assertEqual(rows[1]['종목명'],'SK하이닉스')
        self.assertIsNone(rows[1]['종가 (원)'])
        self.assertTrue(comparison_warnings(rows))

    def test_mismatched_period_basis_and_date(self):
        results={code:{'metrics':{'year':2026,'quarter':q,'basis':basis},
                      'lamp':{'date':day}} for code,q,basis,day in
                 [('005930',2,'CFS','2026-10-01'),('000660',1,'OFS','2026-09-30')]}
        rows=comparison_rows(list(results),results)
        self.assertEqual(len(comparison_warnings(rows)),3)
        self.assertEqual(comparison_warnings(rows[:1]),[])

    def test_csv_preserves_codes_and_escapes_names(self):
        rows=comparison_rows(['005930'],{}, {'005930':'=HYPERLINK("x")'})
        data=comparison_csv(rows)
        self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
        self.assertIn("'005930",data.decode('utf-8-sig'))
        self.assertIn("'=HYPERLINK",data.decode('utf-8-sig'))
        self.assertNotIn('classroom_credentials',data.decode('utf-8-sig'))

    def test_nonfinite_values_are_missing(self):
        rows=comparison_rows(['005930'],{'005930':{'lamp':{'close':float('nan')},
            'krx':{'market_cap':float('inf')}}})
        self.assertIsNone(rows[0]['종가 (원)'])
        self.assertIsNone(rows[0]['시가총액 (억원)'])


if __name__=='__main__':unittest.main()
