#!/usr/bin/perl
# 
# prcs2hg: convert a PRCS repository to Mercurial
# Copyright (C) 2010 Kaz Sasa.
# 
# Revision History
# 
# ------------------------------------------------------------------------------
# 0.1.1 - Fausto Marzoli (Feb 2012)
# - New minor version 0.1 (as new features were added) with new associated branch
# - Comment message in commit as temp file with hg --logfile option
# - Handles filenames with spaces
# - Sub help function
# - Option -p (no prefix to branches)
# - Option -t (add a version tag with major and minor release)
# - Option -m (ask for comment message in commit if original is empty)
# - Added revision history at the top of the file
# ------------------------------------------------------------------------------
# 6 Kaz Sasa
# Added a license to prcs2hg.pl
# ------------------------------------------------------------------------------
# 5 Kaz Sasa
# Added the ignore filters
# ------------------------------------------------------------------------------
# 4 Kaz Sasa
# Modified a make rule
# ------------------------------------------------------------------------------
# 3 Kaz Sasa
# These files will be added automatically
# ------------------------------------------------------------------------------
# 2 Kaz Sasa
# Added autoconf/automake source files
# ------------------------------------------------------------------------------
# 1 Kaz Sasa
# Revised handling of version history
# ------------------------------------------------------------------------------
# 0 Kaz Sasa
# Added experimental version
# ------------------------------------------------------------------------------
# 
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

use strict;
use Getopt::Std;
use File::Temp qw(tempdir);
#~ use File::Temp qw(tempfile tempdir);



sub help () {
    print "Usage: prcs2hg [OPTIONS] PRCS-PROJECT\n";
    print "Options:\n";
    print "  -D         debug mode\n";
    print "  -p         no prefix to branches ('default is prcs2hg=')\n";
    print "  -t         add a version tag with major and minor release\n";
    print "  -m         ask for comment message in commit if original is empty\n";
    print "You must create a repository with 'hg init' in empty current directory before\n";
}

$main::VERSION = "0.1";

my %options;
$Getopt::Std::STANDARD_HELP_VERSION = 1;
getopts "Dpmt", \%options;

my $debug = $options{D};
my $optNoprefix = $options{p};
my $optAskMessage = $options{m};
my $optAddVersionTag = $options{t};


if (@ARGV != 1) {
    help();
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
    die "Directory is not clean\nYou must create a repository with 'hg init' in empty current directory before\n";
}
close(HGLOG);

my $workdir = tempdir CLEANUP => 1;

my %identifiers;
my %file_locations;

# Commit messages temporary file (remove the temp file when the reference goes away)
my $tmp_fh = new File::Temp(UNLINK => 1);
print "Commit message temp filename: $tmp_fh\n" if $debug;


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
    # To delete slash before space in filenames
    $descriptor =~ s/\\\s/ /mg;

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
            # Do not add prefix if option -p
            if ($optNoprefix) {
                (system "hg branch -f '$major'") == 0 or die;
            }
            else {
                (system "hg branch -f 'prcs2hg=$major'") == 0 or die;
            }
        }
    }
    
    # Ask for messages if option -m
    if ($optAskMessage && ($message eq "(no message)")) {
        print "Version $major.$minor does not have a commit message\n";
        print "You can add here (CTRL-D to finish):\n";
        # chomp ($message = <>);
        $message = join'', <STDIN>;
    }
    truncate($tmp_fh, 0);
    seek($tmp_fh, 0, 0);
    # Trim
    $message =~ s/^\s+//;
    $message =~ s/\s+$//;
    print $tmp_fh "$message";
#    (system "hg commit -m '$message' -d '$date' -u '$user'") == 0 or die;
    (system "hg commit -l $tmp_fh -d '$date' -u '$user'") == 0 or die;
    
    # Add tag with minor version if option -t
    if ($optAddVersionTag) {
        (system "hg tag $major.$minor") == 0 or die;
    }
    
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
    help()
}


























