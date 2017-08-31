#!/bin/sh
set -e
#
# This script is meant for quick & easy install via:
#   'curl -sSL https://github.com/rapydo/do/blob/master/install_prerequisites.sh | sh'
# or:
#   'wget -qO- https://github.com/rapydo/do/blob/master/install_prerequisites.sh | sh'
#


# In case you need some parameter
# mirror=''
# while [ $# -gt 0 ]; do
# 	case "$1" in
# 		--mirror)
# 			mirror="$2"
# 			shift
# 			;;
# 		*)
# 			echo "Illegal option $1"
# 			;;
# 	esac
# 	shift $(( $# > 0 ? 1 : 0 ))
# done

command_exists() {
	command -v "$@" > /dev/null 2>&1
}

# Check if this is a forked Linux distro
check_forked() {

	# Check for lsb_release command existence, it usually exists in forked distros
	if command_exists lsb_release; then
		# Check if the `-u` option is supported
		set +e
		lsb_release -a -u > /dev/null 2>&1
		lsb_release_exit_code=$?
		set -e

		# Check if the command has exited successfully, it means we're in a forked distro
		if [ "$lsb_release_exit_code" = "0" ]; then
			# Print info about current distro
			cat <<-EOF
			You're using '$lsb_dist' version '$dist_version'.
			EOF

			# Get the upstream release info
			lsb_dist=$(lsb_release -a -u 2>&1 | tr '[:upper:]' '[:lower:]' | grep -E 'id' | cut -d ':' -f 2 | tr -d '[[:space:]]')
			dist_version=$(lsb_release -a -u 2>&1 | tr '[:upper:]' '[:lower:]' | grep -E 'codename' | cut -d ':' -f 2 | tr -d '[[:space:]]')

			# Print info about upstream distro
			cat <<-EOF
			Upstream release is '$lsb_dist' version '$dist_version'.
			EOF
		else
			if [ -r /etc/debian_version ] && [ "$lsb_dist" != "ubuntu" ] && [ "$lsb_dist" != "raspbian" ]; then
				# We're Debian and don't even know it!
				lsb_dist=debian
				dist_version="$(cat /etc/debian_version | sed 's/\/.*//' | sed 's/\..*//')"
				case "$dist_version" in
					9)
						dist_version="stretch"
					;;
					8|'Kali Linux 2')
						dist_version="jessie"
					;;
					7)
						dist_version="wheezy"
					;;
				esac
			fi
		fi
	fi
}


do_install() {
	architecture=$(uname -m)
	case $architecture in
		# officially supported
		amd64|x86_64)
			;;
		# unofficially supported with available repositories
		armv6l|armv7l)
			;;
		# unofficially supported without available repositories
		aarch64|arm64|ppc64le|s390x)
			cat 1>&2 <<-EOF
			Error: This install script does not support $architecture, because no
			$architecture package exists in Docker's repositories.

			Other install options include checking your distribution's package repository
			for a version of Docker, or building Docker from source.
			EOF
			exit 1
			;;
		# not supported
		*)
			cat >&2 <<-EOF
			Error: $architecture is not a recognized platform.
			EOF
			exit 1
			;;
	esac

	user="$(id -un 2>/dev/null || true)"

	sh_c='sh -c'
	if [ "$user" != 'root' ]; then
		if command_exists sudo; then
			sh_c='sudo -E sh -c'
		elif command_exists su; then
			sh_c='su -c'
		else
			cat >&2 <<-'EOF'
			Error: this installer needs the ability to run commands as root.
			We are unable to find either "sudo" or "su" available to make this happen.
			EOF
			exit 1
		fi
	fi

	# check to see which repo they are trying to install from
	if [ -z "$repo" ]; then
		repo='main'
		if [ "https://test.docker.com/" = "$url" ]; then
			repo='testing'
		elif [ "https://experimental.docker.com/" = "$url" ]; then
			repo='experimental'
		fi
	fi

	# perform some very rudimentary platform detection
	lsb_dist=''
	dist_version=''
	if command_exists lsb_release; then
		lsb_dist="$(lsb_release -si)"
	fi
	if [ -z "$lsb_dist" ] && [ -r /etc/lsb-release ]; then
		lsb_dist="$(. /etc/lsb-release && echo "$DISTRIB_ID")"
	fi
	if [ -z "$lsb_dist" ] && [ -r /etc/debian_version ]; then
		lsb_dist='debian'
	fi
	if [ -z "$lsb_dist" ] && [ -r /etc/fedora-release ]; then
		lsb_dist='fedora'
	fi
	if [ -z "$lsb_dist" ] && [ -r /etc/oracle-release ]; then
		lsb_dist='oracleserver'
	fi
	if [ -z "$lsb_dist" ] && [ -r /etc/centos-release ]; then
		lsb_dist='centos'
	fi
	if [ -z "$lsb_dist" ] && [ -r /etc/redhat-release ]; then
		lsb_dist='redhat'
	fi
	if [ -z "$lsb_dist" ] && [ -r /etc/photon-release ]; then
		lsb_dist='photon'
	fi
	if [ -z "$lsb_dist" ] && [ -r /etc/os-release ]; then
		lsb_dist="$(. /etc/os-release && echo "$ID")"
	fi

	lsb_dist="$(echo "$lsb_dist" | tr '[:upper:]' '[:lower:]')"

	# Special case redhatenterpriseserver
	if [ "${lsb_dist}" = "redhatenterpriseserver" ]; then
        	# Set it to redhat, it will be changed to centos below anyways
        	lsb_dist='redhat'
	fi

	case "$lsb_dist" in

		ubuntu)
			if command_exists lsb_release; then
				dist_version="$(lsb_release --codename | cut -f2)"
			fi
			if [ -z "$dist_version" ] && [ -r /etc/lsb-release ]; then
				dist_version="$(. /etc/lsb-release && echo "$DISTRIB_CODENAME")"
			fi
		;;

		debian|raspbian)
			dist_version="$(cat /etc/debian_version | sed 's/\/.*//' | sed 's/\..*//')"
			case "$dist_version" in
				9)
					dist_version="stretch"
				;;
				8)
					dist_version="jessie"
				;;
				7)
					dist_version="wheezy"
				;;
			esac
		;;

		oracleserver)
			# need to switch lsb_dist to match yum repo URL
			lsb_dist="oraclelinux"
			dist_version="$(rpm -q --whatprovides redhat-release --queryformat "%{VERSION}\n" | sed 's/\/.*//' | sed 's/\..*//' | sed 's/Server*//')"
		;;

		fedora|centos|redhat)
			dist_version="$(rpm -q --whatprovides ${lsb_dist}-release --queryformat "%{VERSION}\n" | sed 's/\/.*//' | sed 's/\..*//' | sed 's/Server*//' | sort | tail -1)"
		;;

		"vmware photon")
			lsb_dist="photon"
			dist_version="$(. /etc/os-release && echo "$VERSION_ID")"
		;;

		*)
			if command_exists lsb_release; then
				dist_version="$(lsb_release --codename | cut -f2)"
			fi
			if [ -z "$dist_version" ] && [ -r /etc/os-release ]; then
				dist_version="$(. /etc/os-release && echo "$VERSION_ID")"
			fi
		;;


	esac

	# Check if this is a forked Linux distro
	check_forked

	cat <<-EOF
		LSB_DIST = ${lsb_dist} echo: DIST_VERSION = ${dist_version}
	EOF


	# Run setup for each distro accordingly
	case "$lsb_dist" in
		ubuntu|debian|raspbian)
			export DEBIAN_FRONTEND=noninteractive

			# set -x; $sh_c 'sleep 3; apt-get update' 
			set -x; $sh_c 'sleep 3; apt-get install -y -q python3'

			exit 0
			;;

		fedora|centos|redhat|oraclelinux|photon)

			if [ "$lsb_dist" = "fedora" ] && [ "$dist_version" -ge "22" ]; then
				(
					set -x
					$sh_c 'sleep 3; dnf -y -q install python3'
				)
			elif [ "$lsb_dist" = "photon" ]; then
				(
					set -x
					$sh_c 'sleep 3; tdnf -y install python3'
				)
			else
				(
					set -x
					$sh_c 'sleep 3; yum -y -q install python3'
				)
			fi
			exit 0
			;;
	esac

	# intentionally mixed spaces and tabs here -- tabs are stripped by "<<-'EOF'", spaces are kept in the output
	cat >&2 <<-'EOF'

	  Your platform is not easily detectable and is not supported by this
	  installer script. Please contact us
	EOF
	exit 1
}

# wrapped up in a function so that we have some protection against only getting
# half the file during "curl | sh"
do_install