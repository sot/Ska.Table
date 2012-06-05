from setuptools import setup
setup(name='Ska.Table',
      author = 'Tom Aldcroft',
      description='Read data tables',
      author_email = 'taldcroft@cfa.harvard.edu',
      test_suite="test",
      py_modules = ['Ska.Table'],
      version='0.05',
      zip_safe=False,
      packages=['Ska'],
      package_dir={'Ska' : 'Ska'},
      package_data={}
      )

