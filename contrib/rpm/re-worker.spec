%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python2_sitearch: %global python2_sitearch %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

%global _pkg_name reworker

Name: re-worker
Summary: Reference base for re-worker plugins
Version: 0.0.7
Release: 1%{?dist}

Group: Applications/System
License: AGPLv3
Source0: %{_pkg_name}-%{version}.tar.gz
Url: https://github.com/rhinception/re-worker

BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
Requires: python-setuptools
Requires: python-argparse
Requires: python-pika
# BuildRequires: python-nose
# %{?el6:BuildRequires: python-unittest2}

%description
This library provides a simple base for release engine workers to
build from.

To implement a worker subclass off of reworker.worker.Worker and
override the process method. If there are any inputs that need to be
passed in the class level variable dynamic should be populated.

%prep
%setup -q -n %{_pkg_name}-%{version}

%build
%{__python2} setup.py build

%install
%{__python2} setup.py install -O1 --root=$RPM_BUILD_ROOT --record=re-worker-files.txt
mkdir -p $RPM_BUILD_ROOT/%{python2_sitelib}/replugin/
touch $RPM_BUILD_ROOT/%{python2_sitelib}/replugin/__init__.py

%files -f re-worker-files.txt
%defattr(-, root, root)
%dir %{python2_sitelib}/%{_pkg_name}
%doc README.md LICENSE AUTHORS
%{python2_sitelib}/replugin/__init__.py*

%changelog
* Tue Dec 16 2014 Steve Milner <stevem@gnulinux.net> - 0.0.7-1
- utils module created.

* Tue Nov  4 2014 Tim Bielawa <tbielawa@redhat.com> - 0.0.6-2
- Change SSL connect params to only use TLS

* Tue Nov  4 2014 Tim Bielawa <tbielawa@redhat.com> - 0.0.6-1
- Now with ability to connect to rabbitmq over SSL. Also automatic port
  selection and defaults.

* Fri Oct 10 2014 Steve Milner <stevem@gnulinux.net> - 0.0.5-2
- python-pika is a requirement

* Fri Oct 3 2014 Steve Milner <stevem@gnulinux.net> - 0.0.5-1
- Workers should attempt to reconnect when disconnected.

* Thu Sep 18 2014 Tim Bielawa <tbielawa@redhat.com> - 0.0.4-6
- re-worker should send to a blank exchange for FSM responses

* Thu Sep  4 2014 Tim Bielawa <tbielawa@redhat.com> - 0.0.4-5
- Relocate initial phase notification logic into the FSM

* Tue Jun 24 2014 Ryan Cook <rcook@redhat.com> - 0.0.4-4
- Added dependency python-argparse for workers

* Tue Jun 24 2014 Steve Milner <stevem@gnulinux.net> - 0.0.4-3
- Start notifications now can happen.

* Tue Jun 24 2014 Steve Milner <stevem@gnulinux.net> - 0.0.4-2
- reply_to now defaults to log.

* Tue Jun 24 2014 Steve Milner <stevem@gnulinux.net> - 0.0.4-1
- Switched target/corr_id in notify.

* Tue Jun 24 2014 Steve Milner <stevem@gnulinux.net> - 0.0.3-1
- Worker class now sends notification when needed.

* Mon Jun 23 2014 Tim Bielawa <tbielawa@redhat.com> - 0.0.2-9
- Add timestamps to Starting/Finished messages

* Fri Jun 20 2014 Steve Milner <stevem@gnulinux.net> - 0.0.2-8
- Added ability to change output level.

* Wed Jun 18 2014 Steve Milner <stevem@gnulinux.net> - 0.0.2-7
- Defattr not being used in files section.

* Tue Jun 17 2014 Ryan Cook <rcook@redhat.com> - 0.0.2-6
- Created the __init__.py to resolve issue when installing re-worker-sleep and re-worker-juicer

* Mon Jun  9 2014 Ryan Cook <rcook@redhat.com> - 0.0.2-5
- Updated for python-setuptools requirement

* Thu Jun  5 2014 Steve Milner <stevem@gnulinux.net> - 0.0.2-4
- Removed check to make rpmlint happy.

* Thu May 22 2014 Tim Bielawa <tbielawa@redhat.com> - 0.0.2-3
- Fix incorrect assignment

* Thu May 22 2014 Tim Bielawa <tbielawa@redhat.com> - 0.0.2-2
- Don't forget about python-setuptools

* Thu May 22 2014 Tim Bielawa <tbielawa@redhat.com> - 0.0.2-1
- Workers can define their own custom queue suffix if desired

* Sun May 11 2014 Tim Bielawa <tbielawa@redhat.com> - 0.0.1-1
- First release
