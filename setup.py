from setuptools import setup
setup(name='Ska.Table',
      author = 'Tom Aldcroft',
      description='Read data tables',
      author_email = 'taldcroft@cfa.harvard.edu',
      test_suite="test",
      py_modules = ['Ska.Table'],
      version='0.01',
      zip_safe=False,
      namespace_packages=['Ska'],
      packages=['Ska'],
      package_dir={'Ska' : 'Ska'},
      package_data={}
      )

