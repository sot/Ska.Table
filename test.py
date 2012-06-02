from Ska.Table import read_table, read_ascii_table, read_fits_table, read_vots_table
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
cols["t/multi-dim.fits"] = ('img_loc_i', 'img_loc_j', 'bad_region', 'flat_row0', 'flat_col0', 'dark_row0',
                            'dark_col0', 'flat_field', 'dark_current', 'fd_y_star', 'fd_z_star',
                            'fd_y_fid', 'fd_z_fid', 'fd_r_star', 'fd_c_star', 'fd_r_fid', 'fd_c_fid',
                            'star_comp_coeffs', 'fm_corr_i', 'fm_corr_j', 'cti_corr_i', 'cti_corr_j',
                            'color_corr_i', 'color_corr_j', 'read_noise', 'gain', 'sub_pix_resp',
                            'aca_align', 'aca_misalign', 'fts_misalign',
                            'psf_lib', 'psf_corr', 'mag0', 'cnt_rate_mag0')
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
nrows["t/multi-dim.fits"] = 1
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
            data_array = read_table(f, **parseopt)
            self.assertEqual(data_array.dtype.names, cols[f])
            self.assertEqual(len(data_array), nrows[f])

    def test2_missing_file(self):
        self.assertRaises(IOError,
                          read_table,
                          'file_doesnt_exist')

    def test3_read_vots_file(self):
        header, data = read_vots_table('t/vots_spec.dat')
        cols = ('id', 'name', 'ra', 'dec', 'flux')
        nrows = 3
        self.assertEqual(data.dtype.names, cols)
        self.assertEqual(len(data), nrows)
        self.assertEqual(header['param'].field('name').tolist(),
                         ['version', 'date'])

    def test4_ascii_colnames(self):
        colnames = ('c1','c2','c3', 'c4', 'c5', 'c6')
        data = read_ascii_table('t/simple3.txt',
                                 colnames=colnames)
        self.assertEqual(data.dtype.names, colnames)

if __name__ == '__main__':
    unittest.main()
