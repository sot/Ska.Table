import sys
import re
import numpy
import csv

class ParseLinesError(ValueError):
    pass

class ParseTableError(ValueError):
    pass

# Single and double quotes (for ease of reading later)
_sq = "'"
_dq = '"'

# Null file-like object.  Needed because pyfits spews warnings to stdout
class _NullFile:
    def write(self, data): pass
    def writelines(self, lines): pass
    def flush(self): pass
    def close(self): pass

class _ParseDialect(object):
    def __str__(self):
        return str((self.quotechar, self.skipinitialspace, self.delimiter, self.comment))

def _parse_ascii_lines(lines, dialect):
    """
    Attempt to parse the supplied table lines given the csv dialect values.
    Problems result in a ParseLinesError exception.  If successful, the number
    of warnings and the lines (parsed into columns) is returned.
    """
    reader = csv.reader(lines,
                        delimiter=dialect.delimiter,
                        skipinitialspace=dialect.skipinitialspace,
                        quotechar=dialect.quotechar,
                        )
    
    n_col_dist = set()                  # Record of values of n_cols that have been seen
    warnings = 0                        # Count of parse conditions that are not ideal, but acceptable
    otherquotechar = {_dq:_sq, _sq:_dq}[dialect.quotechar]
    parsed_lines = []

    for parsed_line in reader:
        # Count the number of parsed columns and bail if equal to one
        n_cols = len(parsed_line)
        if n_cols == 1:
            raise ParseLinesError, 'Got only one column'

        # Clean leading/trailing spaces if needed
        if dialect.cleanspaces:
            parsed_line = [x.strip() for x in parsed_line]

        warnings += len(filter(lambda x: x.startswith(otherquotechar) and x.endswith(otherquotechar),
                               parsed_line))

        # Bail if different rows had different numbers of columns
        n_col_dist.add(n_cols)
        if len(n_col_dist) > 1:
            raise ParseLinesError, 'Multiple number of columns for this dialect'

        # So far so good -- store the parsed line
        parsed_lines.append(parsed_line)

    dialect.n_cols = n_cols
    return warnings, parsed_lines
        
def _make_record_array(array, headerrow, datastart, headertype, colnames):
    # Deprecated way of specifying header/data row info
    if headertype is not None:
        if headertype == 'names':
            headerrow = 1
            datastart = 2
        elif headertype == 'rdb':
            headerrow = 1
            datastart = 3
        elif headertype == 'none':
            headerrow = None
            datastart = None
        else:
            raise ParseTableError, "headertype must be 'names', 'rdb', or 'none'"

    if headerrow:
        header = array[headerrow-1]
    else:
        headerrow = 0
        header = ['col%d' % (i+1) for i in range(len(array[0]))]

    if datastart is None:
        datastart = headerrow+1
    data = array[datastart-1:]

    could_be_int = [True] * len(header)
    could_be_float = [True] * len(header)

    ncols = len(header)
    nrows = len(data)
    
    for c in xrange(ncols):
        for r in xrange(nrows):
            if could_be_float[c]:
                try:
                    x = float(data[r][c])
                except ValueError:
                    could_be_float[c] = False
            if could_be_int[c]:
                try:
                    x = int(data[r][c])
                except ValueError:
                    could_be_int[c] = False
            if not could_be_int[c] and not could_be_float[c]:
                break
    
    for c in xrange(ncols):
        for r in xrange(nrows):
            if could_be_int[c]:
                data[r][c] = int(data[r][c])
            elif could_be_float[c]:
                data[r][c] = float(data[r][c])

    return numpy.rec.fromrecords(data, names=(colnames or header))

def read_ascii_table(indata, headerrow=1, datastart=None, **opt):
    """
    Read the given ASCII data table (supplied as a list of strings or a file object).  Try
    each of the delimiters and quotechars in order and stop for the first case gives a
    sensible result.  Returns a numpy record array object of the data table.

    Allowed values of the ``headertype`` parameter are:
     
    ========  ==============================================================
    name      first row consists of column names
    rdb       first row consists of column names, second row gets ignored
    none      column names auto-generated as col1, col2, ...
    ========  ==============================================================

    :param indata: File name or iterable file-like or list object
    :param delimiters: List of single character delimiters (no RE because csv can't do this)
    :param comment: RE for comment line if matched at beginning (can be a compiled re)
    :param quotechars: List of possible quote characters
    :param cleanspaces: Clean leading/trailing space chars from input lines and output data fields
    :param headerrow: Row number of header (default=1, None => column names auto-generated)
    :param datastart: Row number of data start (default=None => headerrow+1)
    :param headertype: Deprecated, use headerrow and datastart instead.
    :param colnames: Explicitly set column names from list
    :param loud: Print debug info

    """

    try:
        # Assume the indata parameter is a string file name and see how it goes
        lines = open(indata, 'r')
    except TypeError:
        # Should be something iterable
        if not hasattr(indata, '__iter__'):
            raise TypeError, 'Need to supply a readable file name or iterable (list or file) object'
        lines = indata
    dialect, parsed_lines = _parse_ascii_table(lines, **opt)
    data_recarray = _make_record_array(parsed_lines, headerrow, datastart,
                                       opt.get('headertype'), opt.get('colnames'))
    data_recarray.parse_table_dialect = dialect
    data_recarray.colnames = data_recarray.dtype.names
    return data_recarray

def _parse_ascii_table(lines,
                       delimiters=['|', '&', ',', '\t' ,' '],
                       comment=r' *#',
                       quotechars=[_dq, _sq],
                       cleanspaces=True,
                       headertype='names',
                       loud=None,
                       colnames=None,
                      ):

    # Make sure the quotechars list is valid
    if not set(quotechars) <= set([_dq, _sq]):
        raise ParseTableError, "quotechars list can only contain a single or double quote"

    dialect_for = {}
    parsed_lines_for = {}
    re_comment = re.compile(comment)
    debug = (loud and sys.stderr) or _NullFile()

    # Make a copy in memory of in_lines with comments removed
    data_lines = [x for x in lines if not re_comment.match(x)]

    # Try to parse using each combination of quotechar and delimiter
    for quotechar in quotechars:
        for delimiter in delimiters:
            # Create a dialect instance to manage the dialect settings
            dialect = _ParseDialect()
            dialect.comment = comment
            dialect.skipinitialspace = (cleanspaces or delimiter == ' ')
            dialect.delimiter = delimiter
            dialect.quotechar = quotechar
            dialect.cleanspaces = cleanspaces

            # Optionally clean spaces from start and end of each input data line.
            # For the 'space' delimiter this is always done.
            if dialect.skipinitialspace:
                lines = [x.strip() for x in data_lines]
            else:
                lines = data_lines

            print >>debug, 'TRYING dialect ',dialect,':',
            try:
                (warnings, parsed_lines) = _parse_ascii_lines(lines, dialect)
            except ParseLinesError, e:
                print >>debug, e
                continue

            # If everything parsed with no warnings then we're done
            if warnings == 0:
                print >>debug, 'Good'
                return dialect, parsed_lines
            else:
                # Otherwise keep the results keyed by the number of warnings
                print >>debug, "Found warnings: ", warnings
                dialect_for[warnings] = dialect
                parsed_lines_for[warnings] = parsed_lines
        # end delimiter
    # end quotechar

    # At this point none of the attempted dialects was perfect.  See what can be salvaged.
    try:
        # If some dialect parsed the data, but gave some warnings (e.g. values were left
        # with leading and trailing quotes), then use the dialect with the fewest warnings
        fewest_warnings = sorted(dialect_for.keys())[0]
        return dialect_for[fewest_warnings], parsed_lines_for[fewest_warnings]
    except IndexError:
        # Found no dialect that split the data lines sensibly (or else it is just a
        # one column table)
        return None, [[x.strip()] for x in lines]

def _parse_vots_header(lines, **opt):
    """Parse VOTS header fields from 'lines', which should be an
    iterable that returns lines of the VOTS table.  Returns an dict
    of header fields where all but 'description' are in turn a numpy
    recarray table."""
    header = {}
    keywords = ('DESCRIPTION::', 'COOSYS::', 'PARAM::', 'FIELD::')
    key = 'none'
    for line in lines:
        line = line.strip()
        if line in keywords:
            key = line[:-2].lower()
            continue
        if key not in header:
            header[key] = []
        header[key].append(line)

    for key, val in header.items():
        # Get rid of all blank lines at the end of the val list
        while (len(val)>0 and re.search(r'$\s*^', val[-1])):
            val.pop()

        # Flatten description key, otherwise parse lines as a table
        if key == 'description':
            header[key] = '\n'.join(header[key])
        elif len(val) > 0:
            header[key] = read_ascii_table(val, **opt)

    return header

def read_vots_table(indata,
                     delimiters=[' '],
                     quotechars=["'"],
                     cleanspaces=True,
                     loud=False,
                     ):
    """
    Read the given VOTS (VOTable Simple) data table (supplied as a list of
    strings or a file object).  Try each of the delimiters and quotechars in
    order and stop for the first case gives a sensible result.

    :param indata: File name or iterable file-like or list object
    :param delimiters: List of single character delimiters (no RE because csv can't do this)
    :param quotechars: List of possible quote characters
    :param cleanspaces: Clean leading/trailing space chars from input lines and output data fields
    :param loud: Print debug info

    :rtype: (header, data)

    header: dict containing VOTS header elements
    data: numpy record array object of the data table.
    """
    try:
        # Assume the indata parameter is a string file name and see how it goes
        lines = open(indata, 'r')
    except TypeError:
        # Should be something iterable
        if not hasattr(indata, '__iter__'):
            raise TypeError, 'Need to supply a readable file name or iterable (list or file) object'
        lines = indata

    headerlines = []
    datalines = []
    for line in lines:
        line = line.strip()
        if line.startswith('##'):
            continue
        if line.startswith('#'):
            headerlines.append(line[1:])
        else:
            datalines.append(line)

    header = _parse_vots_header(headerlines,
                                delimiters=delimiters,
                                quotechars=quotechars,
                                cleanspaces=cleanspaces,
                                loud=loud,
                                )
    data = read_ascii_table(datalines,
                             headertype='none',
                             delimiters=delimiters,
                             quotechars=quotechars,
                             cleanspaces=cleanspaces,
                             loud=loud,
                             colnames=header['field'].field('name').tolist(),
                             )
    return header, data


def read_fits_table(infile, hdunum=1, pyfits=False):
    """Use pyfits to read the first HDU of the FITS table file 'infile'.  Returns a
    record array object which can be accessed either by row or column, e.g. data[2]
    or data.field('col1').

    :param hdunum: HDU number for desired table (default=1)
    :param pyfits: Return as a pyfits.NP_pyfits.FITS_rec instead of numpy.rec.recarray.
    :rtype: Table object
    """
    # import pyfits as pf so the pyfits keyword is not clobbered
    import pyfits as pf
    hdu = pf.open(infile)[hdunum]
    if pyfits:
        out = hdu.data
    else:
        # Remake array to ensure native datatypes (i.e. match the endianness of
        # the processor).  Some numpy routines (e.g. searchsorted) don't notice
        # the dtype endianness specification and can fail.
        dtypes = []
        colnames = hdu.data.dtype.names
        for colname in colnames:
            col = hdu.data.field(colname)
            if col.dtype.isnative:
                dtype = (colname, col.dtype)
            else:
                dtype = (colname, col.dtype.type) 
            if len(col.shape) > 1:
                dtype = dtype + (tuple(col.shape[1:]),)
            dtypes.append(dtype)

        # Now define a new recarray and copy the original data
        # Note: could use numpy.empty to generate a structured array.
        out = numpy.recarray(len(hdu.data), dtype=dtypes)
        for colname in colnames:
            out[colname][:] = hdu.data.field(colname)

    return out
    
def read_table(file_or_data, **opt):
    """
    All-purpose function to guess the format of a data table and read via the
    format-specific parsers.  First tries FITS then ASCII.

    :param file_or_data: Name of a file or some iterable object with the data
    :param opt: Other options specific to the format (see read_ascii_table and read_fits_table)
    :rtype: Table object
    """
    _sys_stdout = sys.stdout
    try:
        sys.stdout = _NullFile()
        data = read_fits_table(file_or_data, **opt)
        sys.stdout = _sys_stdout
    except (TypeError,IndexError,IOError):
        sys.stdout = _sys_stdout
        data = read_ascii_table(file_or_data, **opt)
    except:
        sys.stdout = _sys_stdout
        raise

    return data

def write_fits_table(outfile, recarray, header={}, clobber=True,
                     units={}, nulls={}, bscales={}, bzeros={}, disps={}):
    """Write ``recarray`` to a FITS binary table file.

    NOTES:
      - Set the binary table extension name with ``header['extname']``
      - Vector column elements should work.  Column elements with 2 or more
        dimensions have not been tested and may have row-ordering issues.

    :param outfile: output file name
    :param recarray: input data (numpy record array)
    :param header: dict of header keyword values
    :param clobber: overwrite existing file (default True)
    :param units: dict specifying column unit values
    :param nulls: dict specifying column null values
    :param bscales: dict specifying column bscale values
    :param bzeros: dict specifying column bzero values
    :param disps: dict specifying column disp values
    :rtype: None
    """
    import pyfits
    np2fits = dict(b1 = 'L',  bool='L', u1 = 'B', i1 = 'I', i2 = 'I', i4 = 'J',
                   i8 = 'J', f4 = 'E', f8 = 'D', c8 = 'C', c16 = 'M')

    colnames = recarray.dtype.names
    coldefs = []
    dims = {}
     
    for colname in colnames:
        datacol = recarray[colname]

        np_kind = datacol.dtype.kind
        np_size = str(datacol.dtype.itemsize)
        np_fmt = np_kind + np_size
        try:
            size = datacol[0].size
            fits_fmt = str(size) + np2fits[np_fmt]
            if size > 1:
                dims[colname] = "(%s)" % ",".join(str(x) for x in datacol[0].shape)
        except KeyError :
            if np_kind == 'S':
                fits_fmt = np_size + 'A' 
            else:
                raise ValueError('Numpy dtype %s is not supported' % np_fmt)

        coldefs.append(pyfits.Column(name=colname,
                                     format=fits_fmt,
                                     array=datacol,
                                     unit=units.get(colname, None),
                                     null=nulls.get(colname, None),
                                     dim=dims.get(colname, None),
                                     bscale=bscales.get(colname, None),
                                     bzero=bzeros.get(colname, None),
                                     disp=disps.get(colname, None)))
    
    cols=pyfits.ColDefs(coldefs)
    hdu0 = pyfits.PrimaryHDU()
    hdu1 = pyfits.new_table(cols)
    for hdr, val in header.items():
        hdu1.header.update(hdr, val)
    hdulist = pyfits.HDUList([hdu0, hdu1]) 

    # Temporarily redirect stdout to suppress the clobber warning message
    # then actually write the file
    try:
        _sys_stdout = sys.stdout
        sys.stdout = _NullFile()
        hdulist.writeto(outfile, clobber=clobber)
    finally:
        sys.stdout = _sys_stdout


