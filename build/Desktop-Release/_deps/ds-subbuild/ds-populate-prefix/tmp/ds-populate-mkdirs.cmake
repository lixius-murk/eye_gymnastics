# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION 3.5)

file(MAKE_DIRECTORY
  "/home/felix/repo/eye_gymnastics/build/Desktop-Release/_deps/ds-src"
  "/home/felix/repo/eye_gymnastics/build/Desktop-Release/_deps/ds-build"
  "/home/felix/repo/eye_gymnastics/build/Desktop-Release/_deps/ds-subbuild/ds-populate-prefix"
  "/home/felix/repo/eye_gymnastics/build/Desktop-Release/_deps/ds-subbuild/ds-populate-prefix/tmp"
  "/home/felix/repo/eye_gymnastics/build/Desktop-Release/_deps/ds-subbuild/ds-populate-prefix/src/ds-populate-stamp"
  "/home/felix/repo/eye_gymnastics/build/Desktop-Release/_deps/ds-subbuild/ds-populate-prefix/src"
  "/home/felix/repo/eye_gymnastics/build/Desktop-Release/_deps/ds-subbuild/ds-populate-prefix/src/ds-populate-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/home/felix/repo/eye_gymnastics/build/Desktop-Release/_deps/ds-subbuild/ds-populate-prefix/src/ds-populate-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/home/felix/repo/eye_gymnastics/build/Desktop-Release/_deps/ds-subbuild/ds-populate-prefix/src/ds-populate-stamp${cfgdir}") # cfgdir has leading slash
endif()
