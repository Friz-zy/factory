if [ ! -d "env" ]; then
  virtualenv 'env'
fi

/bin/bash -c ". env/bin/activate; python setup.py install; cd tests; py.test -v; yes | pip uninstall factory" &&
rm -rf build/ dist/ Factory.egg-info/

