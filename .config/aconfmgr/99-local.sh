# Optional machine-local intent, never shared. Sorts before 99-unsorted.sh so
# a capture still lands last and aconfmgr's "sourced after unsorted" warning
# stays quiet. Temporary or machine-only packages go here: AddPackage to retain
# them, IgnorePackage to leave them unmanaged. Otherwise an apply prunes them.

if [[ -f "$config_dir/aconfmgr.local" ]]
then
	source "$config_dir/aconfmgr.local"
fi
