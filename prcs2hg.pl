#!/usr/bin/perl

use strict;
use Getopt::Std;
use File::Temp qw(tempdir);

$main::VERSION = "0.0";

my %options;
$Getopt::Std::STANDARD_HELP_VERSION = 1;
getopts "D", \%options;

my $debug = $options{D};

if (@ARGV != 1) {
    print "Usage: prcs2hg [OPTIONS] PRCS-PROJECT\n";
    exit 0;
}
$main::project = $ARGV[0];

sub get_info ($) {
    my ($versions) = shift;
    my $largest_major = "0";

    local *INFO;
    local $_;
    @$versions = ();
    open INFO, "prcs info --sort=date '$main::project' |" or die "$!\n";
    while (<INFO>) {
        my ($version, $deleted) = /^$main::project (\S+) .+ by \S+( \*DELETED\*)?$/o;
        next if $deleted ne "";
        push @$versions, $version;
        if ($version =~ /(\d+)\.\d+/) {
            $largest_major = $1 if $1 > $largest_major;
        }
    }
    close INFO;

    return $largest_major;
}

my @versions;
my $largest_major = get_info \@versions;

# To check the current directory is ready for conversion.
open HGLOG, "hg status -X '.$main::project.prcs_aux' |" or die "Current directory is not a repository\n";
while (<HGLOG>) {
    die "Directory is not clean\n";
}
close(HGLOG);

my $workdir = tempdir CLEANUP => 1;

my %identifiers;
my %file_locations;

foreach my $version (@versions) {
    (system "prcs checkout -f -u -r '$version' '$workdir/$main::project' '$workdir/$main::project.prj'") == 0 or die "$!\n";   

    # To check for the parent version.

    open DESCRIPTOR, "$workdir/$main::project.prj" or die "$!\n";
    undef local $/;
    my $descriptor = <DESCRIPTOR>;
    $/ = "\n";
    close DESCRIPTOR;
    unlink "$workdir/$main::project.prj";
    # To delete comments.
    $descriptor =~ s/\s*;.*//mg;

    my ($major, $minor) = $descriptor =~ /\(project-version\s+$main::project\s+(\S+)\s+(\d+)\s*\)/i;
    my $parent_version;
    my ($parent_major, $parent_minor);
    if ($descriptor =~ /\(parent-version\s+$main::project\s+(\S+)\s+(\d+)\s*\)/i) {
        ($parent_major, $parent_minor) = ($1, $2);
        $parent_version = "$parent_major.$parent_minor";
        print STDERR "prcs2hg: Parent version is $parent_version\n" if $debug;
        while (!defined $identifiers{$parent_version}) {
            --$parent_minor;
            die "No appropriate parent found." if $parent_minor == 0;
            $parent_version = "$parent_major.$parent_minor";
        }

        (system "hg update -C -r '$identifiers{$parent_version}' >/dev/null") == 0 or die "$!\n";
    }

    my ($message) = $descriptor =~ /\(version-log\s+"([^"]*)"\s*\)/i;
    my ($date) = $descriptor =~ /\(checkin-time\s+"([^"]*)"\s*\)/i;
    my ($user) = $descriptor =~ /\(checkin-login\s+([^)\s]*)\s*\)/i;
    $message = "(no message)" if $message eq "";
    #print STDERR "message=$message date=$date user=$user\n" if $debug;

    # To handle renames.

    $file_locations{$version} = {};

    my ($files) = $descriptor =~ /\(files\s+((?:\s*\([^()]*\([^()]*\)[^()]*\))*)\s*\)/i;
    #print $files;
    while ($files =~ /\(\s*$workdir\/([^()]*)\s+\(([^()]*)\)(?:\s+([^)]*))?\s*\)/gc) {
        my ($file, $id, $options) = ($1, $2, $3);
        #print STDERR "file=$file id=$id options=$options\n" if $debug;
        next if $options =~ /:symlink\b/; # To ignore symlinks.

        $id =~ s/\s.*//;
        if (defined $parent_version) {
            if (defined $file_locations{$parent_version}->{$id} &&
                $file_locations{$parent_version}->{$id} ne $file) {
                (system "hg rename '$file_locations{$parent_version}->{$id}' '$file'") == 0 or die "$!\n";
            }
        }
        $file_locations{$version}->{$id} = $file;
    }
    if (defined $parent_version) {
        while (my ($id, $file) = each %{$file_locations{$parent_version}}) {
            if (!defined $file_locations{$version}->{$id}) {
                (system "hg remove '$file'") == 0 or die "$!\n";
            }
        }
    }

    #

    (system "prcs checkout -f -u -r '$version' '$main::project' 2>/dev/null") == 0 or die "$!\n";

    while (my ($id, $file) = each %{$file_locations{$version}}) {
        if (!defined $parent_version) {
            (system "hg add '$file'") == 0 or die "$!\n";
        }
        else {
            if (!defined $file_locations{$parent_version}->{$id}) {
                (system "hg add '$file'") == 0 or die "$!\n";
            }
        }
    }

    if (!defined $parent_version) {
        (system "hg add '$main::project.prj'") == 0 or die "$!\n";
    }

    if ($parent_major ne $major) {
        if ($major eq $largest_major) {
            (system "hg branch -f default") == 0 or die;
        }
        else {
            (system "hg branch -f 'prcs2hg=$major'") == 0 or die;
        }
    }
    (system "hg commit -m '$message' -d '$date' -u '$user'") == 0 or die;
    open IDENTIFY, "hg identify -i |" or die "$!\n";
    $identifiers{$version} = <IDENTIFY>;
    chomp $identifiers{$version};
}

sub main::VERSION_MESSAGE {
    my ($file, $getopt, $version, $switches) = shift;
    print $file "prcs2hg $main::VERSION\n";
}

sub main::HELP_MESSAGE {
    my ($file, $getopt, $version, $switches) = shift;
    print $file "Usage: prcs2hg [OPTIONS] PRCS-PROJECT\n";
}
