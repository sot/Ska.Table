from ParseTable import parse_table, parse_ascii_table, parse_fits_table, parse_vots_table
import unittest
from tempfile import mkdtemp

cols = {}
cols["t/short.tab"]      = ('agasc_id', 'n_noids', 'n_obs')
cols["t/simple5.txt"]    = ('3102  |  0.32     |     4167 |  4085   |  Q1250+568-A  |  9',)
cols["t/ascii_ephin.fits"] = ('TIME', 'TLM_FMT', 'SCP4', 'SCP8', 'SCH8', 'SCE150',
                              'SCE300', 'SCE1300', 'SCE3000', 'SCINT', 'SCP25', 'SCP41', 'SCH25', 'SCH41')
cols["t/short.rdb"]      = ('agasc_id', 'n_noids', 'n_obs')
cols["t/apostrophe.tab"] = ('agasc_id', 'n_noids', 'n_obs')
cols["t/apostrophe.rdb"] = ('agasc_id', 'n_noids', 'n_obs')
cols["t/multi-dim.fits"] = ('RA', 'DEC', 'RA_ERR', 'DEC_ERR', 'X', 'Y', 'X_ERR', 'Y_ERR', 'CELL_X', 'CELL_Y',
                            'DETSIZE', 'BKGSIZE', 'NPIXSOU', 'NPIXBKG', 'NET_COUNTS', 'NET_COUNTS_ERR',
                            'BKG_COUNTS', 'BKG_COUNTS_ERR', 'NET_RATE', 'NET_RATE_ERR', 'BKG_RATE', 'BKG_RATE_ERR',
                            'EXPTIME', 'SNR', 'SHAPE', 'R', 'ROTANG', 'PSFRATIO', 'BLOCK', 'COMPONENT', 'EXPO_RATIO',
                            'DOUBLE', 'DOUBLE_ID')
cols["t/simple3.txt"]    = ('obsid', 'redshift', 'X', 'Y', 'object', 'rad')
cols["t/simple4.txt"]    = ('col1', 'col2', 'col3', 'col4', 'col5', 'col6')
cols["t/test4.dat"]      = ('zabs1.nh', 'p1.gamma', 'p1.ampl', 'statname', 'statval')
cols["t/multi.fits"]     = ('APERTURE', 'NPOINTS', 'WAVELENGTH', 'DELTAW', 'NET', 'BACKGROUND', 'SIGMA',
                            'QUALITY', 'FLUX')
cols["t/simple.txt"]     = ('test 1a', 'test2', 'test3', 'test4')
cols["t/simple2.txt"]    = ('obsid', 'redshift', 'X', 'Y', 'object', 'rad')
cols["t/nls1_stackinfo.dbout"] = ('', 'objID', 'osrcid', 'xsrcid', 'SpecObjID', 'ra', 'dec',
                                  'obsid', 'ccdid', 'z', 'modelMag_i',
                                  'modelMagErr_i', 'modelMag_r', 'modelMagErr_r', 'expo',
                                  'theta', 'rad_ecf_39', 'detlim90', 'fBlim90')


nrows = {}
nrows["t/short.tab"] = 7
nrows["t/simple5.txt"] = 2
nrows["t/ascii_ephin.fits"] = 112
nrows["t/short.rdb"] = 7
nrows["t/apostrophe.tab"] = 3
nrows["t/apostrophe.rdb"] = 2
nrows["t/multi-dim.fits"] = 13
nrows["t/simple3.txt"] = 2
nrows["t/simple4.txt"] = 3
nrows["t/test4.dat"] = 1172
nrows["t/multi.fits"] = 1
nrows["t/simple.txt"] = 2
nrows["t/simple2.txt"] = 3
nrows["t/nls1_stackinfo.dbout"] = 58

opt = {}
opt['t/short.rdb'] = {'headertype': 'rdb'}
opt['t/apostrophe.rdb'] = {'headertype': 'rdb'}
opt['t/simple4.txt'] = {'headertype': 'none'}
opt["t/nls1_stackinfo.dbout"] = {'headerrow': 1, 'datastart': 3}

class TestConvert(unittest.TestCase):
    def test1_read_all_files(self):
        from glob import glob
        for f in glob('t/*'):
            if f.endswith('~') or f.endswith('CVS') or f not in cols:
                continue
            parseopt = (f in opt and opt[f]) or {}
            data_array = parse_table(f, **parseopt)
            self.assertEqual(data_array.dtype.names, cols[f])
            self.assertEqual(len(data_array), nrows[f])

    def test2_missing_file(self):
        self.assertRaises(IOError,
                          parse_table,
                          'file_doesnt_exist')

    def test3_read_vots_file(self):
        header, data = parse_vots_table('t/vots_spec.dat')
        cols = ('id', 'name', 'ra', 'dec', 'flux')
        nrows = 3
        self.assertEqual(data.dtype.names, cols)
        self.assertEqual(len(data), nrows)
        self.assertEqual(header['param'].field('name').tolist(),
                         ['version', 'date'])

    def test4_ascii_colnames(self):
        colnames = ('c1','c2','c3', 'c4', 'c5', 'c6')
        data = parse_ascii_table('t/simple3.txt',
                                 colnames=colnames)
        self.assertEqual(data.dtype.names, colnames)

if __name__ == '__main__':
    unittest.main()
