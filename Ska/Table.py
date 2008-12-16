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

def parse_ascii_table(indata, headerrow=1, datastart=None, **opt):
    """
    Parse the given ASCII data table (supplied as a list of strings or a file object).  Try
    each of the delimiters and quotechars in order and stop for the first case gives a
    sensible result.  Returns a numpy record array object of the data table.
    
    indata     : File name or iterable file-like or list object
    delimiters : List of single character delimiters (no RE because csv can't do this)
    comment    : RE for comment line if matched at beginning (can be a compiled re)
    quotechars : List of possible quote characters
    cleanspaces: Clean leading/trailing space chars from input lines and output data fields
    headerrow  : Row number of header (default=1, None => column names auto-generated)
    datastart  : Row number of data start (default=None => headerrow+1)
    headertype : Deprecated, use headerrow and datastart instead.
                 Can be 'names' => first row consists of column names
                        'rdb'   => first row consists of column names, second row gets ignored
                        'none'  => column names auto-generated as col1, col2, ...
    colnames   : Explicitly set column names from list
    loud       : Print debug info
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
            header[key] = parse_ascii_table(val, **opt)

    return header

def parse_vots_table(indata,
                     delimiters=[' '],
                     quotechars=["'"],
                     cleanspaces=True,
                     loud=False,
                     ):
    """
    Parse the given VOTS (VOTable Simple) data table (supplied as a list of
    strings or a file object).  Try each of the delimiters and quotechars in
    order and stop for the first case gives a sensible result.
    Input:     
     indata     : File name or iterable file-like or list object
     delimiters : List of single character delimiters (no RE because csv can't do this)
     quotechars : List of possible quote characters
     cleanspaces: Clean leading/trailing space chars from input lines and output data fields
     loud       : Print debug info

    Returns (header, data):
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
    data = parse_ascii_table(datalines,
                             headertype='none',
                             delimiters=delimiters,
                             quotechars=quotechars,
                             cleanspaces=cleanspaces,
                             loud=loud,
                             colnames=header['field'].field('name').tolist(),
                             )
    return header, data


def parse_fits_table(infile, hdunum=1, pyfits=False):
    """Use pyfits to read the first HDU of the FITS table file 'infile'.  Returns a
    record array object which can be accessed either by row or column, e.g. data[2]
    or data.field('col1').

    hdunum : HDU number for desired table (default=1)
    pyfits : Return as a pyfits.NP_pyfits.FITS_rec instead of numpy.rec.recarray.
    """
    import pyfits as pf
    hdu = pf.open(infile)[hdunum]
    if pyfits:
        out = hdu.data
    else:
        out = numpy.rec.array(hdu.data, dtype=hdu.data.dtype)

    out.colnames = out.dtype.names
    return out
    
def parse_table(file_or_data, **opt):
    """All-purpose function to guess the format of a data table and parse via the
    format-specific parsers.

    file_or_data : Name of a file or some iterable object with the data
    <**opt>      : Other options specific to the parse format (see parse_ascii_table
                   and parse_fits_table)
    """
    _sys_stdout = sys.stdout
    try:
        sys.stdout = _NullFile()
        data = parse_fits_table(file_or_data, **opt)
        sys.stdout = _sys_stdout
    except (TypeError,IndexError):
        sys.stdout = _sys_stdout
        data = parse_ascii_table(file_or_data, **opt)
    except:
        sys.stdout = _sys_stdout
        raise

    return data

def main():
    from glob import glob
    for f in glob('*.txt') + glob('*.rdb') + glob('*.fits') + ['nope.fits']:
        print "File", f
        data_array = parse_table(f) # , loud=True)
        print data_array.dtype.names

if __name__ == '__main__':
    main()
