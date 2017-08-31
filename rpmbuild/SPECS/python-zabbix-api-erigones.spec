%global pypi_name zabbix-api-erigones

Name:           python-%{pypi_name}
Version:        1.2.4
Release:        1%{?dist}
Summary:        Zabbix API Python Library

License:        LGPLv2
URL:            https://github.com/erigones/zabbix-api/
Source0:        https://files.pythonhosted.org/packages/source/z/%{pypi_name}/%{pypi_name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python2-setuptools
 
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

%global desc Zabbix API Python Library.\
\
Used by the Ludolph Monitoring Jabber Bot.\
\
* Supported Python versions: >= 2.6 and >= 3.2\
* Supported Zabbix versions: 1.8, 2.0, 2.2, 2.4, 3.0

%description
%{desc}

%package -n     python2-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python2-%{pypi_name}}

%description -n python2-%{pypi_name}
%{desc}

%package -n     python3-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pypi_name}}

%description -n python3-%{pypi_name}
%{desc}

%prep
%autosetup -n %{pypi_name}-%{version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info

%build
%py2_build
%py3_build

%install
%py2_install
%py3_install


%files -n python2-%{pypi_name}
%doc README.rst
%license LICENSE
%{python2_sitelib}/zabbix_api.py*
%{python2_sitelib}/zabbix_api_erigones-%{version}-py?.?.egg-info

%files -n python3-%{pypi_name}
%doc README.rst
%license LICENSE
%{python3_sitelib}/__pycache__/*
%{python3_sitelib}/zabbix_api.py
%{python3_sitelib}/zabbix_api_erigones-%{version}-py?.?.egg-info

%changelog
* Thu Aug 31 2017 ricco <richard.kellner@gmail.com> - 1.2.4-1
- Initial package.
