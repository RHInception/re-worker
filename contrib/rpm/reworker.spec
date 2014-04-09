%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

Name:           reworker
Version:        0.0.1
Release:        1%{?dist}
Summary:        Common worker framework for Release Engine

License:        AGPLv3+
URL:            https://github.com/RHInception/re-worker
Source0:        reworker-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python-devel, python-pip
Requires:       python-pika>=0.9.12


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
* Tue Apr  9 2014 Steve Milner <stevem@gnulinux.net>- 0.0.1-1
- Initial spec
