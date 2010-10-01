# Contributor: David Gidwani <miniature@archlinux.us>

name=obstartup
pkgname="${name}-hg"
pkgver=1
pkgrel=1
source=()
md5sums=()

url="http://bitbucket.org/darvid"
pkgdesc="A user-friendly Openbox autostart.sh configurator."
license=('BSD')

arch=('x86_64' 'i686')

_hgroot=$url
_hgrepo="$name"

depends=('python' 'pygtk')
makedepends=('mercurial' 'coreutils')

build () {
  cd $srcdir
  msg "Connecting to Mercurial server..."
  if [[ -d "${_hgrepo}/.hg" ]]; then
    ( cd $_hgrepo && hg pull -u )
  else
    hg clone "${_hgroot}/${_hgrepo}"
  fi
  cd "${_hgrepo}"
  install -D -m755 "${name}.py" "${pkgdir}/usr/bin/$name"
}