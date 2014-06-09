%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python2_sitearch: %global python2_sitearch %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

Name:           reworker
Version:        0.0.2
Release:        3%{?dist}
Summary:        Common worker framework for Release Engine

License:        AGPLv3+
URL:            https://github.com/RHInception/re-worker
Source0:        reworker-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python-devel
BuildRequires:  python-setuptools
Requires:       python-pika>=0.9.12
Requires:  python-setuptools


%description
Common worker framework for Release Engine


%prep
%setup -q


%build
%{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT


%files
%doc README.md LICENSE AUTHORS
%{python_sitelib}/*


%changelog
* Mon Jun  9 2014 Ryan Cook <rcook@redhat.com>- 0.0.1-3
- Requires python-setuptools 

* Tue Apr  9 2014 Ryan Cook <rcook@redhat.com>- 0.0.1-2
- Updated to remove python-pip and include python-setuptools

* Tue Apr  9 2014 Steve Milner <stevem@gnulinux.net>- 0.0.1-1
- Initial spec
