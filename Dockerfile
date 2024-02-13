# syntax=docker/dockerfile:1.4

FROM condaforge/mambaforge:latest as builder

RUN mamba update --yes --all
RUN mamba install --yes "boa" "conda-verify"

# Build all custom recipes in one command. We build our own conda packages to simplify
# the environment creation process, as some of them were only available in pypi.
COPY recipes /recipes
RUN for pkg in rmath traits niflow-nipype1-workflows; do \
        conda mambabuild --no-anaconda-upload /recipes/$pkg && \
        conda build purge; \
    done

# RUN for pkg in rmath traits niflow-nypipe-workflows; do \
#         --mount=source=recipes/$pkg,target=/$pkg \
#         conda mambabuild --no-anaconda-upload $pkg && \
#         conda build purge; \
#     done

FROM condaforge/mambaforge:latest as install

COPY --from=builder /opt/conda/conda-bld/ /opt/conda/conda-bld/
RUN mamba install --yes --use-local \
    "python=3.11" "pip" "nodejs" "rmath"
RUN mamba update --yes --all
RUN --mount=source=requirements.txt,target=/requirements.txt \
    --mount=source=requirements-test.txt,target=/requirements-test.txt \
    --mount=source=install-requirements.sh,target=/install-requirements.sh \
    /install-requirements.sh \
    --requirements-file /requirements.txt \
    --requirements-file /requirements-test.txt
RUN mamba clean --yes --all --force-pkgs-dirs \
    && find /opt/conda -follow -type f -name "*.a" -delete \
    && rm -rf /opt/conda/conda-bld

FROM nipreps/fmriprep:20.2.7

RUN mkdir /ext /host \
    && chmod a+rwx /ext /host

ENV PATH="/opt/conda/bin:$PATH" \
    MAMBA_EXE="/opt/conda/bin/mamba"

# Use `/var/cache` for downloaded resources instead of
# `/home/fmriprep/.cache`, because it is less likely to be
# obscured by default container bind mounts when running
# with Singularity
ENV XDG_CACHE_HOME="/var/cache" \
    HALFPIPE_RESOURCE_DIR="/var/cache/halfpipe" \
    TEMPLATEFLOW_HOME="/var/cache/templateflow"
RUN mv /home/fmriprep/.cache/templateflow /var/cache

# Re-install `conda` and all `python` packages
RUN rm -rf /opt/conda
COPY --from=install /opt/conda/ /opt/conda/

# Re-apply matplotlib settings after updating
# Taken from `fmriprep`
# Pre-caches fonts, set 'Agg' as default backend for matplotlib
RUN python -c "from matplotlib import font_manager" \
    && sed -i '/backend:/s/^#*//;/^backend/s/: .*/: Agg/' \
    $( python -c "import matplotlib; print(matplotlib.matplotlib_fname())" )

# Download all resources
RUN --mount=source=src/halfpipe/resource.py,target=/resource.py \
    python /resource.py

# Add coinstac server components
COPY --from=coinstacteam/coinstac-base:latest /server/ /server/

# Install HALFpipe
RUN --mount=target=/halfpipe \
    cp -r /halfpipe /tmp \
    && pip install --no-deps /tmp/halfpipe \
    && rm -rf ~/.cache/pip /var/cache/pip /tmp/* /var/tmp/* \
    && sync

ENTRYPOINT ["/opt/conda/bin/halfpipe"]
